#!/usr/bin/env python3

# kimnaty
# Copyright (C) 2024  Maurice (mausy5043) Hendrix
# AGPL-3.0-or-later  - see LICENSE

"""Create graphs of the data for various periods."""

import argparse
import json
import random
import sqlite3 as s3
import sys
import time
import warnings
from datetime import datetime as dt

import constants
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# UserWarning: Could not infer format, so each element will be parsed individually,
# falling back to `dateutil`. To ensure parsing is consistent and as-expected,
# please specify a format.
#   df: pd.DataFrame = pd.read_sql_query(
#             s3_query, con, parse_dates=["sample_time"], index_col="sample_epoch"
#         )
warnings.simplefilter(action="ignore", category=UserWarning)

DATABASE = constants.TREND["database"]
TABLE_RHT = constants.TREND["sql_table_rht"]
TABLE_AC = constants.TREND["sql_table_ac"]
ROOMS = constants.ROOMS
DEVICE_LIST = constants.DEVICES
AIRCO_LIST = constants.AIRCO

# fmt: off
parser = argparse.ArgumentParser(description="Create a trendgraph")
parser.add_argument("-hr", "--hours", type=int, help="create hour-trend for last <HOURS> hours")
parser.add_argument("-d", "--days", type=int, help="create day-trend for last <DAYS> days")
parser.add_argument("-m", "--months", type=int, help="number of months of data to use for the graph")
parser.add_argument("-e", "--edate", type=str, help="date of last day of the graph (default: now)")
parser.add_argument("-o", "--outside", action="store_true", help="plot outside temperature")
parser.add_argument("--devlist", type=str, help="quoted python list of device-ids to show; example: \'[\"1.1\", \"0.1\"]\'")
parser_group = parser.add_mutually_exclusive_group(required=False)
parser_group.add_argument("--debug", action="store_true", help="start in debugging mode")
OPTION = parser.parse_args()
# fmt: on

DEBUG = False
EDATETIME = "'now'"


def prune(objects: list) -> list:
    """Remove all entries from `objects` that are not in OPTION.devlist"""
    return_objects = []
    for device in objects:
        if str(device["room_id"]) in OPTION.devlist:
            return_objects.append(device)
    return return_objects


def fetch_data(hours_to_fetch: int = 48, aggregation: str = "10min") -> dict:
    """..."""
    data_dict_rht = fetch_data_rht(hours_to_fetch=hours_to_fetch, aggregation=aggregation)
    data_dict_ac = fetch_data_ac(hours_to_fetch=hours_to_fetch, aggregation=aggregation)
    data_dict = {}
    # move outside temperature from Daikin to the table with the other temperature sensors
    #     for d in data_dict_ac:
    #         if "T(out)" in data_dict_ac[d]:
    #             data_dict_rht["temperature"]["T(out)"] = data_dict_ac[d]["T(out)"]
    #             data_dict_ac[d].drop(["T(out)"], axis=1, inplace=True, errors="ignore")s
    for key, value in data_dict_ac.items():
        if "T(out)" in value:
            # pylint: disable=R1733
            data_dict_rht["temperature"]["T(out)"] = data_dict_ac[key]["T(out)"]
            data_dict_ac[key].drop(["T(out)"], axis=1, inplace=True, errors="ignore")
    # for d in data_dict_rht:
    #     data_dict[d] = data_dict_rht[d]
    for key, value in data_dict_rht.items():
        data_dict[key] = value
    # for d in data_dict_ac:
    #     data_dict[d] = data_dict_ac[d]
    for key, value in data_dict_ac.items():
        data_dict[key] = value
    return data_dict


def fetch_data_ac(hours_to_fetch: int = 48, aggregation: str = "10min") -> dict:
    """
    Query the database to fetch the requested data
    :param hours_to_fetch:      (int) number of hours of data to fetch
    :param aggregation:         (int) number of minutes to aggregate per datapoint
    :return:
    """
    df = pd.DataFrame()
    df_cmp = pd.DataFrame()
    df_t = pd.DataFrame()
    if DEBUG:
        print("*** fetching AC ***")
    for airco in AIRCO_LIST:
        airco_id = airco["name"]
        where_condition = (
            f" ( sample_time >= datetime({EDATETIME}, '-{hours_to_fetch + 1} hours')"
            f" AND sample_time <= datetime({EDATETIME}, '+2 hours') )"
            f" AND (room_id LIKE '{airco_id}')"
        )
        s3_query = f"SELECT * FROM {TABLE_AC} WHERE {where_condition}"  # nosec B608
        if DEBUG:
            print(s3_query)
        # Get the data
        success = False
        retries = 5
        while not success and retries > 0:
            try:
                with s3.connect(DATABASE) as con:
                    df: pd.DataFrame = pd.read_sql_query(
                        s3_query, con, parse_dates=["sample_time"], index_col="sample_epoch"
                    )
                    success = True
            except (s3.OperationalError, pd.errors.DatabaseError) as exc:
                if DEBUG:
                    print("Database may be locked. Waiting...")
                retries -= 1
                time.sleep(random.randint(30, 60))  # nosec bandit B311
                if retries == 0:
                    raise TimeoutError("Database seems locked.") from exc

        for c in df.columns:
            if c not in ["sample_time"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df.index = (
            pd.to_datetime(df.index, unit="s").tz_localize("UTC").tz_convert("Europe/Amsterdam")
        )
        df.drop("sample_time", axis=1, inplace=True, errors="ignore")
        # resample to monotonic timeline
        df = df.resample(f"{aggregation}").mean(numeric_only=True)
        df = df.interpolate()
        # remove temperature target values for samples when the AC is turned off.
        df.loc[df.ac_power == 0, "temperature_target"] = np.nan
        # conserve memory; we dont need these anymore.
        df.drop(["ac_mode", "ac_power", "room_id"], axis=1, inplace=True, errors="ignore")
        df_cmp = collate(
            df_cmp,
            df,
            columns_to_drop=["temperature_ac", "temperature_target", "temperature_outside"],
            column_to_rename="cmp_freq",
            new_name=airco_id,
        )
        if df_t.empty:
            df1 = collate(
                None,
                df,
                columns_to_drop=["cmp_freq", "temperature_outside"],
                column_to_rename="temperature_ac",
                new_name=airco_id,
            )
            df_t = collate(
                df_t,
                df1,
                columns_to_drop=[],
                column_to_rename="temperature_target",
                new_name=f"{airco_id}_tgt",
            )
        else:
            df2 = collate(
                None,
                df,
                columns_to_drop=["cmp_freq"],
                column_to_rename="temperature_ac",
                new_name=airco_id,
            )
            df_t = collate(
                df_t,
                df2,
                columns_to_drop=[],
                column_to_rename="temperature_target",
                new_name=f"{airco_id}_tgt",
            )

    # create a new column containing the max value of both aircos, then remove the airco_ columns
    df_cmp["cmp_freq"] = df_cmp[["airco0", "airco1"]].apply(np.max, axis=1)
    df_cmp.drop(["airco0", "airco1"], axis=1, inplace=True, errors="ignore")
    # if DEBUG:
    #     print(df_cmp)
    # rename the column to something shorter or drop it
    if OPTION.outside:
        df_t.rename(columns={"temperature_outside": "T(out)"}, inplace=True)
    else:
        df_t.drop(["temperature_outside"], axis=1, inplace=True, errors="ignore")
    if DEBUG:
        print(df_t)

    ac_data_dict: dict[str, pd.DataFrame] = {"temperature_ac": df_t, "compressor": df_cmp}
    return ac_data_dict


def fetch_data_rht(hours_to_fetch: int = 48, aggregation: str = "10min") -> dict:
    """
    Query the database to fetch the requested data
    :param hours_to_fetch:      (int) number of hours of data to fetch
    :param aggregation:         (int) number of minutes to aggregate per datapoint
    :return:
    """
    df = pd.DataFrame()
    if DEBUG:
        print("*** fetching RHT ***")
    df_t = pd.DataFrame()
    df_h = pd.DataFrame()
    df_v = pd.DataFrame()
    for device in DEVICE_LIST:
        room_id = device["room_id"]
        where_condition = (
            f" ( sample_time >= datetime({EDATETIME}, '-{hours_to_fetch + 1} hours')"
            f" AND sample_time <= datetime({EDATETIME}, '+2 hours') )"
            f" AND (room_id LIKE '{room_id}')"
        )
        s3_query = f"SELECT * FROM {TABLE_RHT} WHERE {where_condition}"  # nosec B608
        if DEBUG:
            print(s3_query)
        # Get the data
        success = False
        retries = 5
        while not success and retries > 0:
            try:
                with s3.connect(DATABASE) as con:
                    df: pd.DataFrame = pd.read_sql_query(
                        s3_query, con, parse_dates=["sample_time"], index_col="sample_epoch"
                    )
                    success = True
            except (s3.OperationalError, pd.errors.DatabaseError) as exc:
                if DEBUG:
                    print("Database may be locked. Waiting...")
                retries -= 1
                time.sleep(random.randint(30, 60))  # nosec bandit B311
                if retries == 0:
                    raise TimeoutError("Database seems locked.") from exc

        # conserve memory; we dont need the room_id repeated in every row.
        df.drop("room_id", axis=1, inplace=True, errors="ignore")
        for c in df.columns:
            if c not in ["sample_time"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df.index = (
            pd.to_datetime(df.index, unit="s").tz_localize("UTC").tz_convert("Europe/Amsterdam")
        )
        # resample to monotonic timeline
        df = df.resample(f"{aggregation}").mean(numeric_only=True)
        df = df.interpolate()
        try:
            new_name = ROOMS[room_id]
        except KeyError:
            new_name = room_id
        df.drop("sample_time", axis=1, inplace=True, errors="ignore")
        # if DEBUG:
        #     print(df)
        df_t = collate(
            df_t,
            df,
            columns_to_drop=["voltage", "humidity"],
            column_to_rename="temperature",
            new_name=new_name,
        )

        df_h = collate(
            df_h,
            df,
            columns_to_drop=["temperature", "voltage"],
            column_to_rename="humidity",
            new_name=new_name,
        )

        df_v = collate(
            df_v,
            df,
            columns_to_drop=["temperature", "humidity"],
            column_to_rename="voltage",
            new_name=new_name,
        )

    if DEBUG:
        print(f"TEMPERATURE\n{df_t.head()}")
        print(f"TEMPERATURE\n{df_t.tail()}")
    #     print(f"HUMIDITY\n{df_h}")
    #     print(f"VOLTAGE\n{df_v}")
    rht_data_dict: dict[str, pd.DataFrame] = {
        "temperature": df_t,
        "humidity": df_h,
        "voltage": df_v,
    }
    return rht_data_dict


def collate(
    prev_df: pd.DataFrame | None,
    data_frame: pd.DataFrame,
    columns_to_drop: list,
    column_to_rename: str,
    new_name: str = "room_id",
) -> pd.DataFrame:
    # drop the 'columns_to_drop'
    if not columns_to_drop:
        columns_to_drop = []
    for col in columns_to_drop:
        data_frame = data_frame.drop(col, axis=1, errors="ignore")
    # rename the 'column_to_rename'
    data_frame.rename(columns={f"{column_to_rename}": new_name}, inplace=True)
    # if DEBUG:
    #     print()
    #     print(new_name)
    #     print(data_frame)
    # collate both dataframes
    if prev_df is not None:
        data_frame = pd.merge(prev_df, data_frame, left_index=True, right_index=True, how="outer")
    # if DEBUG:
    #     print(data_frame)
    return data_frame


def plot_graph(output_file: str, data_dict: dict, plot_title: str) -> None:
    """Plot the data into a graph

    Args:
        output_file (str): (str) name of the trendgraph file
        data_dict (dict): contains the data for the lines.
                          Each parameter is a separate pandas Dataframe
                          e.g. {'df': Dataframe}
        plot_title (str): title to be displayed above the plot
    Returns:
        None
    """
    if DEBUG:
        print("*** plotting ***")
    for parameter_name in data_dict:
        parameter = str(parameter_name)
        if DEBUG:
            print(parameter)
        data_frame = data_dict[parameter]
        fig_x = 20
        fig_y = 7.5
        fig_fontsize = 13
        ahpla = 0.7

        # ###############################
        # Create a line plot of temperatures
        # ###############################

        plt.rc("font", size=fig_fontsize)
        ax1 = data_frame.plot(kind="line", marker=".", figsize=(fig_x, fig_y))
        # linewidth and alpha need to be set separately
        for _, _l in enumerate(ax1.lines):  # pylint: disable=W0612
            plt.setp(_l, alpha=ahpla, linewidth=1, linestyle=" ")
        ax1.set_ylabel(parameter)
        if parameter == "temperature_ac":
            ax1.set_ylim((12.0, 28.0))
        if parameter == "voltage":
            ax1.set_ylim((2.2, 3.3))
        ax1.legend(loc="lower left", ncol=8, framealpha=0.2)
        ax1.set_xlabel("Datetime")
        ax1.grid(which="major", axis="y", color="k", linestyle="--", linewidth=0.5)
        plt.title(f"{parameter} {plot_title}")
        plt.tight_layout()
        plt.savefig(
            fname=f"{output_file}_{parameter}.png",
            format="png",
            # bbox_inches='tight'
        )


def main() -> None:
    """
    This is the main loop
    """
    try:
        if OPTION.hours:
            # aggr = int(float(OPTION.hours) * 60. / 480.)
            # if aggr < 1:
            #     aggr = 1
            aggr = "2min"
            plot_graph(
                constants.TREND["day_graph"],
                fetch_data(hours_to_fetch=OPTION.hours, aggregation=aggr),
                f" trend afgelopen dagen ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
            )
        if OPTION.days:
            # aggr = int(float(OPTION.days) * 24. * 60. / 5760.)
            # if aggr < 1:
            #     aggr = 30
            aggr = "h"
            plot_graph(
                constants.TREND["month_graph"],
                fetch_data(hours_to_fetch=OPTION.days * 24, aggregation=aggr),
                f" trend per uur afgelopen maand ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
            )
        if OPTION.months:
            # aggr = int(float(OPTION.months) * 30.5 * 24. * 60. / 9900.)
            # if aggr < 1:
            #     aggr = 30
            aggr = "6h"
            plot_graph(
                constants.TREND["year_graph"],
                fetch_data(hours_to_fetch=OPTION.months * 31 * 24, aggregation=aggr),
                f" trend per dag afgelopen maanden ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
            )
    except pd.errors.DatabaseError:
        # Database is locked let it go...
        print("Failing due to database error (locked?)")


if __name__ == "__main__":
    if OPTION.debug:
        print(OPTION)
        DEBUG = True
        print("DEBUG-mode started")

    print(f"Trending with Python {sys.version}")

    # use hardcoded default if CLI value is 0
    if OPTION.hours == 0:
        OPTION.hours = constants.TREND["option_hours"]
    if OPTION.days == 0:
        OPTION.days = constants.TREND["option_days"]
    if OPTION.months == 0:
        OPTION.months = constants.TREND["option_months"]
    if not OPTION.outside:
        OPTION.outside = constants.TREND["option_outside"]
    if OPTION.devlist:
        # convert parameter to Python list()
        OPTION.devlist = json.loads(OPTION.devlist)
        DEVICE_LIST = prune(DEVICE_LIST)
    if OPTION.edate:
        print("NOT NOW")
        EDATETIME = f"'{OPTION.edate}'"
    if OPTION.debug:
        print(OPTION)
    main()

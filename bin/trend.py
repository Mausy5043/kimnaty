#!/usr/bin/env python3

"""Create trendbargraphs of the data for various periods."""

import argparse
from datetime import datetime as dt
import sqlite3 as s3
import pandas as pd

import matplotlib.pyplot as plt
import numpy as np

import constants

# import libtrend as lt

DATABASE = constants.TREND['database']
TABLE = constants.TREND['sql_table']
DEVICE_LIST = constants.DEVICES
OPTION = ""
DEBUG = False


def fetch_data(hours_to_fetch=48, aggregation=1):
    """
    Query the database to fetch the requested data
    :param hours_to_fetch:      (int) number of hours of data to fetch
    :param aggregation:         (int) number of minutes to aggregate per datapoint
    :return:
    """
    global DATABASE
    global TABLE
    global DEVICE_LIST
    global DEBUG
    data_dict = dict()
    for device in DEVICE_LIST:
        room_id = device[1]
        where_condition = f" (sample_time >= datetime(\'now\', \'-{hours_to_fetch + 1} hours\'))"
        where_condition += f" AND (room_id LIKE \'{room_id}\')"
        s3_query = f"SELECT * FROM {TABLE} WHERE {where_condition}"
        if DEBUG:
            print(s3_query)
        with s3.connect(DATABASE) as con:
            df = pd.read_sql_query(s3_query,
                                   con,
                                   parse_dates='sample_time',
                                   index_col='sample_epoch'
                                   )
        # conserve memory; we dont need the room_id repeated in every row.
        df = df.drop('room_id', 1)
        for c in df.columns:
            if c not in ['sample_time']:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        df.index = pd.to_datetime(df.index, unit='s').tz_localize("UTC").tz_convert("Europe/Amsterdam")
        # resample to monotonic timeline
        df = df.resample(f'{aggregation}min').mean()
        df = df.interpolate(method='slinear')
        df = df.reset_index(level=['sample_epoch'])
        # remove NaNs
        df = remove_nans(df, 'temperature', 20.0)
        df = remove_nans(df, 'humidity', 50)
        df = remove_nans(df, 'voltage', 1.800)
        if DEBUG:
            print(df)
        data_dict[room_id] = dict()
        data_dict[room_id]['df'] = df
        # TODO: map room names onto room_id
        data_dict[room_id]['name'] = f"room {room_id}"
    return data_dict


def remove_nans(frame, col_name, default):
    """remove NANs from a series"""
    for idx, tmpr in enumerate(frame[col_name]):
        if np.isnan(tmpr):
            if idx == 0:
                frame.at[idx, col_name] = default
            else:
                frame.at[idx, col_name] = frame.at[idx - 1, col_name]
    return frame


def plot_graph(output_file, data_dict, plot_title, show_data=0):
    """...
    """
    data_lbls = data_tuple[0]
    import_lo = data_tuple[1]
    import_hi = data_tuple[2]
    opwekking = data_tuple[3]
    export_lo = data_tuple[4]
    export_hi = data_tuple[5]
    imprt = lt.contract(import_lo, import_hi)
    exprt = lt.contract(export_lo, export_hi)
    own_usage = lt.distract(opwekking, exprt)
    usage = lt.contract(own_usage, imprt)
    btm_hi = lt.contract(import_lo, own_usage)
    """
    --- Start debugging:
    np.set_printoptions(precision=3)
    print("data_lbls: ", np.size(data_lbls), data_lbls[-5:])
    print(" ")
    print("opwekking: ", np.size(opwekking), opwekking[-5:])
    print(" ")
    print("export_hi: ", np.size(export_hi), export_hi[-5:])
    print("export_lo: ", np.size(export_lo), export_lo[-5:])
    print("exprt    : ", np.size(exprt), exprt[-5:])
    print(" ")
    print("import_hi: ", np.size(import_hi), import_hi[-5:])
    print("import_lo: ", np.size(import_lo), import_lo[-5:])
    print("imprt    : ", np.size(imprt), imprt[-5:])
    print(" ")
    print("own_usage: ", np.size(own_usage), own_usage[-5:])
    print("usage    : ", np.size(usage), usage[-5:])
    print(" ")
    print("btm_hi   : ", np.size(btm_hi), btm_hi[-5:])
    --- End debugging.
    """
    # Set the bar width
    bar_width = 0.75
    # Set the color alpha
    ahpla = 0.7
    # positions of the left bar-boundaries
    tick_pos = list(range(1, len(data_lbls) + 1))

    # Create the general plot and the bar
    plt.rc("font", size=6.5)
    dummy, ax1 = plt.subplots(1, figsize=(10, 3.5))
    col_import = "red"
    col_export = "blue"
    col_usage = "green"

    # Create a bar plot of import_lo
    ax1.bar(tick_pos,
            import_hi,
            width=bar_width,
            label="Inkoop (normaal)",
            alpha=ahpla,
            color=col_import,
            align="center",
            bottom=btm_hi,  # [sum(i) for i in zip(import_lo, own_usage)]
            )
    # Create a bar plot of import_hi
    ax1.bar(tick_pos,
            import_lo,
            width=bar_width,
            label="Inkoop (dal)",
            alpha=ahpla * 0.5,
            color=col_import,
            align="center",
            bottom=own_usage,
            )
    # Create a bar plot of own_usage
    ax1.bar(tick_pos,
            own_usage,
            width=bar_width,
            label="Eigen gebruik",
            alpha=ahpla,
            color=col_usage,
            align="center",
            )
    if show_data == 1:
        for i, v in enumerate(own_usage):
            ax1.text(tick_pos[i],
                     10,
                     "{:7.3f}".format(v),
                     {"ha": "center", "va": "bottom"},
                     rotation=-90,
                     )
    if show_data == 2:
        for i, v in enumerate(usage):
            ax1.text(tick_pos[i],
                     500,
                     "{:4.0f}".format(v),
                     {"ha": "center", "va": "bottom"},
                     fontsize=12,
                     )
    # Exports hang below the y-axis
    # Create a bar plot of export_lo
    ax1.bar(tick_pos,
            [-1 * i for i in export_lo],
            width=bar_width,
            label="Verkoop (dal)",
            alpha=ahpla * 0.5,
            color=col_export,
            align="center",
            )
    # Create a bar plot of export_hi
    ax1.bar(tick_pos,
            [-1 * i for i in export_hi],
            width=bar_width,
            label="Verkoop (normaal)",
            alpha=ahpla,
            color=col_export,
            align="center",
            bottom=[-1 * i for i in export_lo],
            )
    if show_data == 1:
        for i, v in enumerate(exprt):
            ax1.text(tick_pos[i],
                     -10,
                     "{:7.3f}".format(v),
                     {"ha": "center", "va": "top"},
                     rotation=-90,
                     )
    if show_data == 2:
        for i, v in enumerate(exprt):
            ax1.text(tick_pos[i],
                     -500,
                     "{:4.0f}".format(v),
                     {"ha": "center", "va": "top"},
                     fontsize=12,
                     )

    # Set Axes stuff
    ax1.set_ylabel("[kWh]")
    if show_data == 0:
        y_lo = -1 * (max(exprt) + 1)
        y_hi = max(usage) + 1
        if y_lo > -1.5:
            y_lo = -1.5
        if y_hi < 1.5:
            y_hi = 1.5
        ax1.set_ylim([y_lo, y_hi])

    ax1.set_xlabel("Datetime")
    ax1.grid(which="major",
             axis="y",
             color="k",
             linestyle="--",
             linewidth=0.5
             )
    ax1.axhline(y=0, color="k")
    ax1.axvline(x=0, color="k")
    # Set plot stuff
    plt.xticks(tick_pos, data_lbls, rotation=-60)
    plt.title(f"{plot_title}")
    plt.legend(loc="upper left", ncol=5, framealpha=0.2)
    # Fit every nicely
    plt.xlim([min(tick_pos) - bar_width, max(tick_pos) + bar_width])
    plt.tight_layout()
    plt.savefig(fname=f"{output_file}", format="png")


def main():
    """
    This is the main loop
    """
    global OPTION

    if OPTION.hours:
        plot_graph(constants.TREND['day_graph'],
                   fetch_data(hours_to_fetch=OPTION.hours, aggregation=1),
                   f"Energietrend afgelopen dagen ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
                   )
    if OPTION.days:
        plot_graph(constants.TREND['month_graph'],
                   fetch_data(hours_to_fetch=OPTION.days * 24, aggregation=60),
                   f"Energietrend per uur afgelopen maand ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
                   )
    if OPTION.months:
        plot_graph(constants.TREND['year_graph'],
                   fetch_data(hours_to_fetch=OPTION.months * 31 * 24, aggregation=60 * 24),
                   f"Energietrend per dag afgelopen maanden ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
                   )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a trendgraph")
    parser.add_argument("-hr",
                        "--hours",
                        type=int,
                        help="create hour-trend for last <HOURS> hours",
                        )
    parser.add_argument("-d",
                        "--days",
                        type=int,
                        help="create day-trend for last <DAYS> days"
                        )
    parser.add_argument("-m",
                        "--months",
                        type=int,
                        help="number of months of data to use for the graph",
                        )
    parser_group = parser.add_mutually_exclusive_group(required=False)
    parser_group.add_argument("--debug",
                              action="store_true",
                              help="start in debugging mode"
                              )
    OPTION = parser.parse_args()
    if OPTION.hours == 0:
        OPTION.hours = 50
    if OPTION.days == 0:
        OPTION.days = 50
    if OPTION.months == 0:
        OPTION.months = 38
    if OPTION.debug:
        DEBUG = True
    print(OPTION)
    main()

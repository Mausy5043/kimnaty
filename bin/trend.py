#!/usr/bin/env python3

"""Create trendbargraphs of the data for various periods."""

import argparse
import copy
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
    df_t = None
    df_h = None
    df_v = None
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
        df = df.drop('room_id', axis=1)
        for c in df.columns:
            if c not in ['sample_time']:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        df.index = pd.to_datetime(df.index, unit='s').tz_localize("UTC").tz_convert("Europe/Amsterdam")
        # resample to monotonic timeline
        df = df.resample(f'{aggregation}min').mean()
        df = df.interpolate(method='slinear')
        # df = df.reset_index(level=['sample_epoch'])
        # remove NaNs
        # df = remove_nans(df, 'temperature', 20.0)
        # df = remove_nans(df, 'humidity', 50)
        # df = remove_nans(df, 'voltage', 1.800)

        df_t0 = copy.deepcopy(df)
        df_t0 = df_t0.drop('humidity', axis=1)
        df_t0 = df_t0.drop('voltage', axis=1)
        df_t0.rename(columns={'temperature': room_id}, inplace=True)
        if df_t is None:
            df_t = df_t0
        else:
            df_t = pd.merge(df_t, df_t0, left_index=True, right_index=True, how='left')  # .fillna(20.0)

        df_h0 = copy.deepcopy(df)
        df_h0 = df_h0.drop('temperature', axis=1)
        df_h0 = df_h0.drop('voltage', axis=1)
        df_h0.rename(columns={'humidity': room_id}, inplace=True)
        if df_h is None:
            df_h = df_h0
        else:
            df_h = pd.merge(df_h, df_h0, left_index=True, right_index=True, how='left')  # .fillna(20.0)

        df_v0 = copy.deepcopy(df)
        df_v0 = df_v0.drop('temperature', axis=1)
        df_v0 = df_v0.drop('humidity', axis=1)
        df_v0.rename(columns={'voltage': room_id}, inplace=True)
        if df_v is None:
            df_v = df_v = df_v0
        else:
            df_v.join(df_v0)
            df_v = pd.merge(df_v, df_v0, left_index=True, right_index=True, how='left')  # .fillna(20.0)
    if DEBUG:
        print(f"TEMPERATURE\n", df_t)
        print(f"HUMIDITY\n", df_h)
        print(f"VOLTAGE\n", df_v)
    data_dict = {'temperature': df_t, 'humidity': df_h, 'voltage': df_v}
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


def plot_graph(output_file, data_dict, plot_title):
    """
    Plot the data into a graph

    :param output_file: (str) name of the trendgraph file
    :param data_dict: (dict) contains the data for the lines. Each location is a separate pandas Dataframe with a roomname
                      {'df': Dataframe, 'name' str }
    :param plot_title: (str) title to be displayed above the plot
    :return: None
    """
    global DEBUG
    # Set the bar width
    bar_width = 0.75
    # Set the color alpha
    ahpla = 0.7
    # positions of the left bar-boundaries
    for parameter in data_dict:
        if DEBUG:
            print(parameter)
        data_frame = data_dict[parameter]
        fig_x = 10
        fig_y = 2.5
        fig_fontsize = 6.5
        ahpla = 0.6
        """
        # ###############################
        # Create a line plot of temperatures
        # ###############################
        """
        plt.rc('font', size=fig_fontsize)
        ax1 = data_frame.plot(kind='line',
                              figsize=(fig_x, fig_y)
                              )
        # linewidth and alpha need to be set separately
        for i, l in enumerate(ax1.lines):
            plt.setp(l, alpha=ahpla, linewidth=1)
        # ax1.set_ylabel("[degC]")
        ax1.legend(loc='upper left',
                   framealpha=0.2
                   )
        ax1.set_xlabel("Datetime")
        ax1.grid(which='major',
                 axis='y',
                 color='k',
                 linestyle='--',
                 linewidth=0.5
                 )
        plt.title(f'{parameter} {plot_title}')
        # plt.tight_layout()
        plt.savefig(fname=f'{output_file}_{parameter}.png', format='png')


def main():
    """
    This is the main loop
    """
    global OPTION

    if OPTION.hours:
        plot_graph(constants.TREND['day_graph'],
                   fetch_data(hours_to_fetch=OPTION.hours, aggregation=1),
                   f" trend afgelopen dagen ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
                   )
    if OPTION.days:
        plot_graph(constants.TREND['month_graph'],
                   fetch_data(hours_to_fetch=OPTION.days * 24, aggregation=60),
                   f" trend per uur afgelopen maand ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
                   )
    if OPTION.months:
        plot_graph(constants.TREND['year_graph'],
                   fetch_data(hours_to_fetch=OPTION.months * 31 * 24, aggregation=60 * 24),
                   f" trend per dag afgelopen maanden ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
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

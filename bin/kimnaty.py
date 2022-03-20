#!/usr/bin/env python3

#
# parser = argparse.ArgumentParser()
# parser.add_argument('mac', help='MAC address of LYWSD03 device', nargs='+')
# args = parser.parse_args()


"""
Communicate with the LYWSD03MMC devices.

Store data from the devices in an sqlite3 database.
"""

import argparse
import datetime as dt
import os
import sqlite3
import sys
import time
import traceback

import mausy5043libs.libsignals3 as ml  # noqa

import constants
import lywsd03mmc

from hanging_threads import start_monitoring

anti_freeze = constants.KIMNATY['report_time'] * 2

parser = argparse.ArgumentParser(description="Execute the telemetry daemon.")
parser_group = parser.add_mutually_exclusive_group(required=True)
parser_group.add_argument("--start",
                          action="store_true",
                          help="start the daemon as a service"
                          )
parser_group.add_argument("--debug",
                          action="store_true",
                          help="start the daemon in debugging mode"
                          )
OPTION = parser.parse_args()

# constants
DEBUG = False
HERE = os.path.realpath(__file__).split("/")
# runlist id :
MYID = HERE[-1]
# app_name :
MYAPP = HERE[-3]
MYROOT = "/".join(HERE[0:-3])
# host_name :
NODE = os.uname()[1]


# example values:
# HERE: ['', 'home', 'pi', 'kimnaty', 'bin', 'kimnaty.py']
# MYID: 'kimnaty.py
# MYAPP: kimnaty
# MYROOT: /home/pi
# NODE: rbenvir


def main():
    """Execute main loop."""
    global DEBUG
    global MYAPP
    global MYROOT
    killer = ml.GracefulKiller()
    start_monitoring(seconds_frozen=anti_freeze, test_interval=1357)
    fdatabase = constants.KIMNATY['database']
    sqlcmd = constants.KIMNATY['sql_command']
    report_time = int(constants.KIMNATY['report_time'])
    sample_time = report_time / int(constants.KIMNATY['samplespercycle'])
    list_of_devices = constants.DEVICES

    test_db_connection(fdatabase)

    pause_time = time.time()
    while not killer.kill_now:
        if time.time() > pause_time:
            start_time = time.time()
            results = do_work(list_of_devices)
            if DEBUG:
                print(f"Result   : {results}")

            # report samples
            if results:
                do_add_to_database(results, fdatabase, sqlcmd)

            pause_time = (sample_time
                          - (time.time() - start_time)
                          - (start_time % sample_time)
                          )
            if pause_time > 0:
                if DEBUG:
                    print(f"Waiting  : {pause_time:.1f}s")
                time.sleep(pause_time)
                if DEBUG:
                    print("................................")
            else:
                if DEBUG:
                    print(f"Behind   : {pause_time:.1f}s")
                    print("................................")
        else:
            time.sleep(1.0)


def do_work(dev_list):
    """Scan the devices to get current readings."""
    global DEBUG
    data_list = list()
    retry_list = list()
    for mac in dev_list:
        succes, data = get_data(mac[0])
        data[0] = mac[1]  # replace mac-address by room-id
        if succes:
            data_list.append(data)
        else:
            retry_list.append(mac)

    if retry_list:
        if DEBUG:
            print("Retrying failed connections in 15s...")
        time.sleep(15.0)
        for mac in retry_list:
            succes, data = get_data(mac[0])
            data[0] = mac[1]  # replace mac-address by room-id
            if succes:
                data_list.append(data)
    return data_list


def get_data(mac):
    """Fetch a data from a device."""
    temperature = 0.0
    humidity = 0
    voltage = 0.0
    success = False
    try:
        client = lywsd03mmc.Lywsd03mmcClient(mac)
        if DEBUG:
            print(f'Fetching data from {mac}')
        data = client.data
        if DEBUG:
            print(f'Temperature       : {data.temperature}°C')
            print(f'Humidity          : {data.humidity}%')
            print(f'Battery           : {data.battery}% ({data.voltage}V)')
            print('')
        temperature = data.temperature
        humidity = data.humidity
        voltage = data.voltage
        success = True
    except Exception as e:
        print("*** While talking to {mac}")
        print("*** This error occured:")
        print(f"    {e}")

    return success, [mac, temperature, humidity, voltage]


def do_add_to_database(results, fdatabase, sql_cmd):
    """Commit the results to the database."""
    # Get the time and date in human-readable form and UN*X-epoch...
    conn = None
    cursor = None
    dt_format = "%Y-%m-%d %H:%M:%S"
    out_date = dt.datetime.now()  # time.strftime('%Y-%m-%dT%H:%M:%S')
    out_epoch = int(out_date.timestamp())
    for data in results:
        result = (out_date.strftime(dt_format),
                  out_epoch,
                  data[0],
                  data[1],
                  data[2],
                  data[3]
                  )
        if DEBUG:
            print(f"   @: {out_date.strftime(dt_format)}")
            print(f"    : {result}")

        err_flag = True
        while err_flag:
            try:
                conn = create_db_connection(fdatabase)
                cursor = conn.cursor()
                cursor.execute(sql_cmd, result)
                cursor.close()
                conn.commit()
                conn.close()
                err_flag = False
            except sqlite3.OperationalError:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()


def get_mac_list(src_file):
    return []


def create_db_connection(database_file):
    """
    Create a database connection to the SQLite3 database specified
    by database_file.
    """
    consql = None
    if DEBUG:
        print(f"Connecting to: {database_file}")
    try:
        consql = sqlite3.connect(database_file, timeout=9000)
        return consql
    except sqlite3.Error:
        print("Unexpected SQLite3 error when connecting to server.")
        print(traceback.format_exc())
        if consql:  # attempt to close connection to SQLite3 server
            consql.close()
            print(" ** Closed SQLite3 connection. **")
        raise


def test_db_connection(fdatabase):
    """
    Test & log database engine connection.
    """
    try:
        conn = create_db_connection(fdatabase)
        cursor = conn.cursor()
        cursor.execute("SELECT sqlite_version();")
        versql = cursor.fetchone()
        cursor.close()
        conn.commit()
        conn.close()
        print(f"Attached to SQLite3 server: {versql}")
    except sqlite3.Error:
        print("Unexpected SQLite3 error during test.")
        print(traceback.format_exc())
        raise


if __name__ == "__main__":
    if OPTION.debug:
        DEBUG = True
        print("Debug-mode started.")
        print("Use <Ctrl>+C to stop.")
        main()

    if OPTION.start:
        main()

    print("And it's goodnight from him")

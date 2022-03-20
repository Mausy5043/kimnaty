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
import re
import sqlite3
import syslog
import time
import traceback

import mausy5043funcs.fileops3 as mf  # noqa
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
    killer = ml.GracefulKiller()
    start_monitoring(seconds_frozen=anti_freeze, test_interval=1357)
    fdatabase = constants.KIMNATY['database']
    sqlcmd = constants.KIMNATY['sql_command']
    report_time = int(constants.KIMNATY['report_time'])
    samples_averaged = int(constants.KIMNATY['samplespercycle']) \
                       * int(constants.KIMNATY['cycles'])
    sample_time = report_time / int(constants.KIMNATY['samplespercycle'])
    data = []

    test_db_connection(fdatabase)

    pause_time = time.time()
    while not killer.kill_now:
        if time.time() > pause_time:
            start_time = time.time()
            result = do_work()
            result = result.split(",")
            mf.syslog_trace(f"Result   : {result}", False, DEBUG)
            # data.append(list(map(int, result)))
            data.append([int(d) for d in result])
            if len(data) > samples_averaged:
                data.pop(0)
            # mf.syslog_trace(f"Data     : {data}", False, DEBUG)

            # report sample average
            if start_time % report_time < sample_time:
                # # somma       = list(map(sum, zip(*data)))
                # somma = [sum(d) for d in zip(*data)]
                # # not all entries should be float
                # # ['3088596', '3030401', '270', '0', '0', '0', '1', '1']
                # # averages    = [format(sm / len(data), '.2f') for sm in somma]
                # averages = data[-1]
                # averages[2] = int(somma[2] / len(data))  # avg powerin
                # averages[5] = int(somma[5] / len(data))  # avg powerout
                # mf.syslog_trace(f"Averages : {averages}", False, DEBUG)
                # if averages[0] > 0:
                do_add_to_database(data, fdatabase, sqlcmd)

            pause_time = (sample_time
                          - (time.time() - start_time)
                          - (start_time % sample_time)
                          + time.time()
                          )
            if pause_time > 0:
                mf.syslog_trace(f"Waiting  : {pause_time - time.time():.1f}s", False, DEBUG)
                time.sleep(pause_time)
                mf.syslog_trace("................................", False, DEBUG)
            else:
                mf.syslog_trace(
                    f"Behind   : {pause_time - time.time():.1f}s", False, DEBUG, )
                mf.syslog_trace("................................", False, DEBUG)
        else:
            # time.sleep(1.0)
            time.sleep(report_time * 0.1)


def do_work(mac_list):
    """Scan the devices to get current readings."""
    block = list()
    retry_list = list()
    for mac in mac_list:
        block.append = get_data(mac)

    return f"{block}"


# noinspection PyUnresolvedReferences
def get_data(mac):
    """Fetch a data from a device."""
    temperature = 0.0
    humidity = 0
    voltage = 0.0
    success = False
    try:
        client = lywsd03mmc.Lywsd03mmcClient(mac)
        mf.syslog_trace(f'Fetching data from {mac}', False, DEBUG)
        data = client.data
        mf.syslog_trace(f'Temperature       : {data.temperature}°C', False, DEBUG)
        temperature = data.temperature
        mf.syslog_trace(f'Humidity          : {data.humidity}%', False, DEBUG)
        humidity = data.humidity
        mf.syslog_trace(f'Battery           : {data.battery}% ({data.voltage}V)', False, DEBUG)
        voltage = data.voltage
        mf.syslog_trace('', False, DEBUG)
        success = True
    except Exception as e:
        mf.syslog_trace("*** While talking to:", syslog.LOG_DEBUG, DEBUG)
        mf.syslog_trace(f"    {mac}", syslog.LOG_DEBUG, DEBUG)
        mf.syslog_trace("*** This error occured:", syslog.LOG_DEBUG, DEBUG)
        mf.syslog_trace(f"    {e}", syslog.LOG_DEBUG, DEBUG)

        loops2go = loops2go - 1
        if loops2go < 0:
            abort = 3

    # test for correct start of telegram
    if telegram[0][0] != "/":
        abort = 2

    if abort == 1:
        with open("/tmp/kimnaty.raw", "w") as output_file:
            for line in telegram:
                output_file.write(f"{line}\n")

    # Return codes:
    # abort == 1 indicates a successful read
    # abort == 2 means that a serial port read/write error occurred
    # abort == 3 no valid data after several attempts
    return success, [mac, temperature, humidity, voltage]


def do_add_to_database(result, fdatabase, sql_cmd):
    """Commit the results to the database."""
    # Get the time and date in human-readable form and UN*X-epoch...
    conn = None
    cursor = None
    dt_format = "%Y-%m-%d %H:%M:%S"
    out_date = dt.datetime.now()  # time.strftime('%Y-%m-%dT%H:%M:%S')
    out_epoch = int(out_date.timestamp())
    results = (out_date.strftime(dt_format),
               out_epoch,
               result[0],
               result[1],
               result[2],
               result[3],
               result[4],
               result[5],
               result[6],
               result[7]
               )
    mf.syslog_trace(f"   @: {out_date.strftime(dt_format)}", False, DEBUG)
    mf.syslog_trace(f"    : {results}", False, DEBUG)

    err_flag = True
    while err_flag:
        try:
            conn = create_db_connection(fdatabase)
            cursor = conn.cursor()
            cursor.execute(sql_cmd, results)
            cursor.close()
            conn.commit()
            conn.close()
            err_flag = False
        except sqlite3.OperationalError:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


def create_db_connection(database_file):
    """
    Create a database connection to the SQLite3 database specified
    by database_file.
    """
    consql = None
    mf.syslog_trace(f"Connecting to: {database_file}", False, DEBUG)
    try:
        consql = sqlite3.connect(database_file, timeout=9000)
        # if consql:    # dB initialised succesfully -> get a cursor on the dB
        #                                               and run a test.
        #  cursql = consql.cursor()
        #  cursql.execute("SELECT sqlite_version()")
        #  versql = cursql.fetchone()
        #  cursql.close()
        #  logtext = f"Attached to SQLite3 server : {versql}"
        #  syslog.syslog(syslog.LOG_INFO, logtext)
        return consql
    except sqlite3.Error:
        mf.syslog_trace("Unexpected SQLite3 error when connecting to server.", syslog.LOG_CRIT, DEBUG)
        mf.syslog_trace(traceback.format_exc(), syslog.LOG_CRIT, DEBUG)
        if consql:  # attempt to close connection to SQLite3 server
            consql.close()
            mf.syslog_trace(" ** Closed SQLite3 connection. **", syslog.LOG_CRIT, DEBUG)
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
        syslog.syslog(syslog.LOG_INFO, f"Attached to SQLite3 server: {versql}")
    except sqlite3.Error:
        mf.syslog_trace("Unexpected SQLite3 error during test.", syslog.LOG_CRIT, DEBUG)
        mf.syslog_trace(traceback.format_exc(), syslog.LOG_CRIT, DEBUG)
        raise


if __name__ == "__main__":
    # initialise logging
    syslog.openlog(ident=f'{MYAPP}.{MYID.split(".")[0]}', facility=syslog.LOG_LOCAL0)

    # noinspection PyUnresolvedReferences
    PORT = serial.Serial()  # pylint: disable=C0103
    PORT.baudrate = 9600
    # noinspection PyUnresolvedReferences
    PORT.bytesize = serial.SEVENBITS
    # noinspection PyUnresolvedReferences
    PORT.parity = serial.PARITY_EVEN
    # noinspection PyUnresolvedReferences
    PORT.stopbits = serial.STOPBITS_ONE
    PORT.xonxoff = 1
    PORT.rtscts = 0
    PORT.dsrdtr = 0
    PORT.timeout = 15
    PORT.port = "/dev/ttyUSB0"

    if OPTION.debug:
        DEBUG = True
        mf.syslog_trace("Debug-mode started.", syslog.LOG_DEBUG, DEBUG)
        print("Use <Ctrl>+C to stop.")

    # OPTION.start only executes this next line, we don't need to test for it.
    main()

    print("And it's goodnight from him")

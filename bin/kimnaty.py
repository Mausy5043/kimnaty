#!/usr/bin/env python3

"""
Communicate with the LYWSD03MMC devices.

Store data from the devices in an sqlite3 database.
"""

import argparse
import datetime as dt
import os
import shutil
import sqlite3 as s3
import syslog
import time
import traceback

import mausy5043_common.funfile as mf
import mausy5043_common.libsignals as ml

import constants
import libdaikin
import pylywsdxx as pyly  # noqa

parser = argparse.ArgumentParser(description="Execute the telemetry daemon.")
parser_group = parser.add_mutually_exclusive_group(required=True)
parser_group.add_argument("--start", action="store_true", help="start the daemon as a service")
parser_group.add_argument(
    "--debug", action="store_true", help="start the daemon in debugging mode"
)
parser_group.add_argument(
    "--debughw", action="store_true", help="start the daemon in hardware debugging mode"
)
OPTION = parser.parse_args()

# constants
DEBUG = False
DEBUG_HW = False
HERE = os.path.realpath(__file__).split("/")
# runlist id :
MYID = HERE[-1]
# app_name :
MYAPP = HERE[-3]
MYROOT = "/".join(HERE[0:-3])
APPROOT = "/".join(HERE[0:-2])
# host_name :
NODE = os.uname()[1]

# example values:
# HERE: ['', 'home', 'pi', 'kimnaty', 'bin', 'kimnaty.py']
# MYID: 'kimnaty.py
# MYAPP: kimnaty
# MYROOT: /home/pi
# NODE: rbenvir


def main():  # noqa: C901
    """Execute main loop."""
    killer = ml.GracefulKiller()
    fdatabase = constants.KIMNATY["database"]
    sqlcmd_rht = constants.KIMNATY["sql_command"]
    sqlcmd_ac = constants.AC["sql_command"]
    report_time = int(constants.KIMNATY["report_time"])
    sample_time = report_time / int(constants.KIMNATY["samplespercycle"])
    list_of_devices = constants.DEVICES
    if DEBUG:
        print(f"report_time : {report_time} s")
        print(list_of_devices)
    list_of_aircos = constants.AIRCO
    for airco in list_of_aircos:
        airco["device"] = libdaikin.Daikin(airco["ip"])
    if DEBUG:
        print(list_of_aircos)

    test_db_connection(fdatabase)

    next_time = time.time()
    while not killer.kill_now:
        if time.time() > next_time:
            start_time = time.time()
            # RH/T
            rht_results = do_work_rht(list_of_devices)
            if DEBUG:
                print(f"Result   : {rht_results}")
            if rht_results:
                do_add_to_database(rht_results, fdatabase, sqlcmd_rht)
            # AC
            ac_results = do_work_ac(list_of_aircos)
            if DEBUG:
                print(f"Result   : {ac_results}")
            # report samples
            if ac_results:
                do_add_to_database(ac_results, fdatabase, sqlcmd_ac)

            if DEBUG:
                print(f" >>> Time to get results: {time.time() - start_time}")

            pause_time = sample_time - (time.time() - start_time) - (start_time % sample_time)
            next_time = time.time() + pause_time
            if pause_time > 0:
                if DEBUG:
                    print(f"Waiting  : {pause_time:.1f}s")
                    print("................................")
                time.sleep(1.0)
            else:
                if DEBUG:
                    print(f"Behind   : {pause_time:.1f}s")
                    print("................................")
        else:
            time.sleep(1.0)


def do_work_rht(dev_list):
    """Scan the devices to get current readings."""
    # possible outcomes for health_score
    # success       +5; current battery level will limit max. score
    # fail+success  -5
    # fail+fail     -10
    data_list = []
    retry_list = []
    for dev in dev_list:
        health_score = 0
        succes, data = get_rht_data(dev[0], f"room {dev[1]}")
        data[2] = dev[1]  # replace mac-address by room-id
        if succes:
            health_score += 5
            set_led(dev[1], "green")
            data_list.append(data)
        else:
            health_score -= 5
            set_led(dev[1], "orange")
            retry_list.append(dev)
        log_health_score(room_id=dev[1], state_change=health_score, battery=data[5])

    if retry_list:
        if DEBUG:
            print("Retrying failed connections...")
        pyly.bt_hardware.ble_reset()
        for dev in retry_list:
            health_score = 0
            succes, data = get_rht_data(dev[0], f"room {dev[1]}")
            data[2] = dev[1]  # replace mac-address by room-id
            if succes:
                health_score += 0
                set_led(dev[1], "green")
                data_list.append(data)
            else:
                health_score -= 5
                set_led(dev[1], "red")
            log_health_score(room_id=dev[1], state_change=health_score, battery=data[5])
    return data_list


def log_health_score(room_id, state_change, battery):
    """Store the state of a device in the database."""
    bat_hi = 3.2
    bat_lo = 2.2
    old_state = constants.get_health(room_id)
    bat_state = (min(max(bat_lo, battery), bat_hi) - bat_lo) / (bat_hi - bat_lo) * 100.0
    state = min(bat_state, old_state) + state_change
    state = int(max(0, min(state, 100)))
    update_cmd = constants.HEALTH_UPDATE["sql_command"] % (state, room_id)
    if DEBUG:
        print(f"{room_id} : previous state = {old_state}; new state = {state}")
        print(f"{update_cmd}")
    do_update_database(fdatabase=constants.KIMNATY["database"], sql_cmd=update_cmd)


def get_rht_data(addr, dev_id):
    """Fetch data from a device."""
    temperature = 0.0
    humidity = 0
    voltage = 0.0
    success = False
    t0 = time.time()
    try:
        client = pyly.Lywsd03client(mac=addr, debug=DEBUG_HW)
        if DEBUG:
            print("")
            print(f"Fetching data from {addr}")
        data = client.data
        if DEBUG:
            print(f"Temperature       : {data.temperature}°C")
            print(f"Humidity          : {data.humidity}%")
            print(f"Battery           : {data.battery}% ({data.voltage}V)")
        temperature = data.temperature
        humidity = data.humidity
        voltage = data.voltage
        success = True
    except BrokenPipeError:
        err_date = dt.datetime.now()
        mf.syslog_trace(
            f"BrokenPipeError on {err_date.strftime(constants.DT_FORMAT)}",
            syslog.LOG_CRIT,
            DEBUG,
        )
    # TODO: catch upstream
    # except pyly.btle.BTLEConnectError:
    #     err_date = dt.datetime.now()
    #     mf.syslog_trace(
    #         f"BTLEConnectError on {err_date.strftime(constants.DT_FORMAT)} for {dev_id} ({addr}) ",
    #         syslog.LOG_CRIT,
    #         DEBUG,
    #     )
    # except pyly.btle.BTLEConnectTimeout:
    #     err_date = dt.datetime.now()
    #     mf.syslog_trace(
    #         f"BTLEConnectTimeout on {err_date.strftime(constants.DT_FORMAT)} for {dev_id} ({addr}) ",
    #         syslog.LOG_CRIT,
    #         DEBUG,
    #     )
    except Exception as her:  # pylint: disable=W0703
        err_date = dt.datetime.now()
        mf.syslog_trace(
            f"*** While talking to {dev_id} ({addr}) error {her} of type of type {type(her).__name__} occured on {err_date.strftime(constants.DT_FORMAT)}",
            syslog.LOG_CRIT,
            DEBUG,
        )
        # mf.syslog_trace(f"    {her}", syslog.LOG_DEBUG, DEBUG)
        mf.syslog_trace(traceback.format_exc(), syslog.LOG_DEBUG, DEBUG)
    if DEBUG:
        print(f"{time.time() - t0:.2f} seconds")
        print("")
    out_date = dt.datetime.now()  # time.strftime('%Y-%m-%dT%H:%M:%S')
    out_epoch = int(out_date.timestamp())

    return success, [
        out_date.strftime(constants.DT_FORMAT),
        out_epoch,
        addr,
        temperature,
        humidity,
        voltage,
    ]


def do_work_ac(dev_list):
    """Scan the devices to get current readings."""
    data_list = []
    retry_list = []
    for airco in dev_list:
        succes, data = get_ac_data(airco)
        if succes:
            data_list.append(data)
        else:
            retry_list.append(airco)

    if retry_list:
        if DEBUG:
            print("Retrying failed connections in 13s...")
        time.sleep(13.0)
        for airco in retry_list:
            succes, data = get_ac_data(airco)
            if succes:
                data_list.append(data)
    return data_list


def get_ac_data(airco):
    """Fetch data from an AC device."""
    ac_pwr = ac_mode = ac_cmp = None
    ac_t_in = ac_t_tgt = ac_t_out = None
    success = False
    t0 = time.time()
    try:
        if DEBUG:
            print(f"Fetching data from {airco['name']}")
        ac_pwr = int(airco["device"].power)
        ac_mode = int(airco["device"].mode)
        ac_cmp = float(airco["device"].compressor_frequency)
        ac_t_in = float(airco["device"].inside_temperature)
        ac_t_out = float(airco["device"].outside_temperature)
        ac_t_tgt = float(airco["device"].target_temperature)
        success = True
    except ValueError:
        # When switched to fan-mode the temperature target becomes '--'
        # When switched to drying mode the temperature target becomes 'M'
        ac_t_tgt = ac_t_in
        success = True
    except Exception as her:  # pylint: disable=W0703
        err_date = dt.datetime.now()
        mf.syslog_trace(
            f"*** While talking to {airco['name']} error {her} of type {type(her).__name__} occured "
            f"on {err_date.strftime(constants.DT_FORMAT)}:",
            syslog.LOG_CRIT,
            DEBUG,
        )
        mf.syslog_trace(traceback.format_exc(), syslog.LOG_DEBUG, DEBUG)
    if DEBUG:
        print(f"+----------------Room {airco['name']} Data----")
        print(f"| T(airco)  : Inside      {ac_t_in:.2f} degC " f"state = {ac_pwr}")
        print(f"|             Target >>>> {ac_t_tgt:.2f} degC " f" mode = {ac_mode}")
        print(f"|             Outside     {ac_t_out:.2f} degC")
        print(f"| compressor: {ac_cmp:.0f} ")
        print("+---------------------------------------------")
        print(f"{time.time() - t0:.2f} seconds\n")

    out_date = dt.datetime.now()  # time.strftime('%Y-%m-%dT%H:%M:%S')
    out_epoch = int(out_date.timestamp())

    return success, [
        out_date.strftime(constants.DT_FORMAT),
        out_epoch,
        airco["name"],
        ac_pwr,
        ac_mode,
        ac_t_in,
        ac_t_tgt,
        ac_t_out,
        ac_cmp,
    ]


def do_add_to_database(results, fdatabase, sql_cmd):
    """Commit the results to the database."""
    conn = None
    cursor = None
    t0 = time.time()
    for data in results:
        result = tuple(data)
        if DEBUG:
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
            except s3.OperationalError:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            except Exception as her:  # pylint: disable=W0703
                err_date = dt.datetime.now()
                mf.syslog_trace(
                    f"*** Error {her} of type {type(her).__name__} occured on {err_date.strftime(constants.DT_FORMAT)}",
                    syslog.LOG_CRIT,
                    DEBUG,
                )
                mf.syslog_trace(traceback.format_exc(), syslog.LOG_DEBUG, DEBUG)
    if DEBUG:
        print(f"{time.time() - t0:.2f} seconds\n")


def do_update_database(fdatabase, sql_cmd):
    """Commit the results to the database."""
    conn = None
    cursor = None
    # t0 = time.time()
    try:
        conn = create_db_connection(fdatabase)
        cursor = conn.cursor()
        cursor.execute(sql_cmd)
        cursor.close()
        conn.commit()
        conn.close()
    except s3.OperationalError:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    except Exception as her:  # pylint: disable=W0703
        err_date = dt.datetime.now()
        mf.syslog_trace(
            f"*** Error {her} of type {type(her).__name__} occured on {err_date.strftime(constants.DT_FORMAT)}",
            syslog.LOG_CRIT,
            DEBUG,
        )
        mf.syslog_trace(traceback.format_exc(), syslog.LOG_DEBUG, DEBUG)
    # if DEBUG:
    #     print(f"{time.time() - t0:.2f} seconds\n")


def create_db_connection(database_file):
    """
    Create a database connection to the SQLite3 database specified
    by database_file.
    """
    consql = None
    if DEBUG:
        print(f"Connecting to: {database_file}")
    try:
        consql = s3.connect(database_file, timeout=9000)
        return consql
    except s3.Error as her:
        mf.syslog_trace(
            f"Unexpected SQLite3 error {her} of type {type(her).__name__} when connecting to server.",
            syslog.LOG_CRIT,
            DEBUG,
        )
        mf.syslog_trace(traceback.format_exc(), syslog.LOG_DEBUG, DEBUG)
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
    except s3.Error as her:
        mf.syslog_trace(f"Unexpected SQLite3 error {her} of type {type(her).__name__} during test.", syslog.LOG_CRIT, DEBUG)
        mf.syslog_trace(traceback.format_exc(), syslog.LOG_DEBUG, DEBUG)
        raise
    except Exception as her:  # pylint: disable=W0703
        err_date = dt.datetime.now()
        mf.syslog_trace(
            f"*** Error {her} of type {type(her).__name__} occured on {err_date.strftime(constants.DT_FORMAT)}",
            syslog.LOG_CRIT,
            DEBUG,
        )
        mf.syslog_trace(traceback.format_exc(), syslog.LOG_DEBUG, DEBUG)


def set_led(dev, colour):
    mf.syslog_trace(f"{dev} is {colour}", False, DEBUG)

    in_dirfile = f"{APPROOT}/www/{colour}.png"
    out_dirfile = f'{constants.TREND["website"]}/img/{dev}.png'
    try:
        shutil.copy(f"{in_dirfile}", out_dirfile)
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    # initialise logging
    syslog.openlog(ident=f'{MYAPP}.{MYID.split(".")[0]}', facility=syslog.LOG_LOCAL0)
    # set-up LEDs
    for device in constants.DEVICES:
        set_led(device[1], "orange")
    if OPTION.debughw:
        DEBUG_HW = True
        OPTION.debug = True
    if OPTION.debug:
        DEBUG = True
        mf.syslog_trace("Debug-mode started.", syslog.LOG_DEBUG, DEBUG)
        print("Use <Ctrl>+C to stop.")
        main()

    if OPTION.start:
        main()

    print("And it's goodnight from him")

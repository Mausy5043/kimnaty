#!/usr/bin/env python3

"""
Communicate with the LYWSD03MMC devices.

Store data from the devices in an sqlite3 database.
"""

import argparse
import datetime as dt
import os
import shutil
import syslog
import time
import traceback

import mausy5043_common.funfile as mf
import mausy5043_common.libsignals as ml
import mausy5043_common.libsqlite3 as m3

import constants
import libdaikin
import pylywsdxx as pyly  # noqa

# fmt: off
parser = argparse.ArgumentParser(description="Execute the telemetry daemon.")
parser_group = parser.add_mutually_exclusive_group(required=True)
parser_group.add_argument("--start", action="store_true", help="start the daemon as a service")
parser_group.add_argument("--debug", action="store_true", help="start the daemon in debugging mode")
parser_group.add_argument("--debughw", action="store_true", help="start the daemon in hardware debugging mode")
OPTION = parser.parse_args()

# constants
DEBUG = False
DEBUG_HW = False
HERE = os.path.realpath(__file__).split("/")  # ['', 'home', 'pi', 'kimnaty', 'bin', 'kimnaty.py']
MYID = HERE[-1]  # 'kimnaty.py'
MYAPP = HERE[-3]  # kimnaty
MYROOT = "/".join(HERE[0:-3])  # /home/pi
APPROOT = "/".join(HERE[0:-2])  # /home/pi/kimnaty
NODE = os.uname()[1]  # rbair
# fmt: on

# class SensorDevice():
#     """..."""

sql_health = m3.SqlDatabase(
    database=constants.HEALTH_UPDATE["database"],
    table=constants.HEALTH_UPDATE["sql_table"],
    insert=constants.HEALTH_UPDATE["sql_command"],
    debug=OPTION.debug,
)


def main():  # noqa: C901
    """Execute main loop."""
    killer = ml.GracefulKiller()

    sql_db_rht = m3.SqlDatabase(
        database=constants.KIMNATY["database"],
        table=constants.KIMNATY["sql_table"],
        insert=constants.KIMNATY["sql_command"],
        debug=DEBUG,
    )

    sql_db_ac = m3.SqlDatabase(
        database=constants.AC["database"],
        table=constants.AC["sql_table"],
        insert=constants.AC["sql_command"],
        debug=DEBUG,
    )

    # fdatabase = constants.KIMNATY["database"]
    # sqlcmd_rht = constants.KIMNATY["sql_command"]
    # sqlcmd_ac = constants.AC["sql_command"]
    report_time = int(constants.KIMNATY["report_time"])
    sample_time = report_time / int(constants.KIMNATY["samplespercycle"])
    list_of_devices = constants.DEVICES
    for bt_dev in list_of_devices:
        bt_dev["device"] = pyly.Lywsd03(mac=bt_dev["mac"], reusable=True, debug=DEBUG_HW)
    if DEBUG:
        print(f"report_time : {report_time} s")
        print(list_of_devices)
    list_of_aircos = constants.AIRCO
    for airco in list_of_aircos:
        airco["device"] = libdaikin.Daikin(airco["ip"])
    if DEBUG:
        print(list_of_aircos)

    next_time = time.time()
    while not killer.kill_now:
        if time.time() > next_time:
            start_time = time.time()
            # RH/T
            rht_results = do_work_rht(list_of_devices)
            if rht_results:
                for element in rht_results:
                    sql_db_rht.queue(element)
            # AC
            ac_results = do_work_ac(list_of_aircos)
            # report samples
            if ac_results:
                for element in ac_results:
                    sql_db_ac.queue(element)

            if DEBUG:
                print(f" >>> Time to get results: {time.time() - start_time}")

            try:
                sql_db_rht.insert(method="replace")
                sql_db_ac.insert(method="replace")
                sql_health.insert(method="replace", index="room_id")
            except Exception as her:  # pylint: disable=W0703
                err_date = dt.datetime.now()
                mf.syslog_trace(
                    f"*** While trying to insert data into the database error {her} "
                    f"of type {type(her).__name__} occured on {err_date.strftime(constants.DT_FORMAT)}",
                    syslog.LOG_CRIT,
                    DEBUG,
                )
                mf.syslog_trace(traceback.format_exc(), syslog.LOG_ALERT, DEBUG)
                raise  # may be changed to pass if errors can be corrected.

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
    """Scan the devices to get current readings.

    Args:
        dev_list: list of dicts with device info

    Returns:
        (list) containing dicts with data
    """

    # possible outcomes for health_score
    # success       +5; current battery level will limit max. score
    # fail+success  -5
    # fail+fail     -10
    data_list = []
    retry_list = []
    for dev in dev_list:
        health_score = 0
        succes, data = get_rht_data(dev)
        if succes:
            health_score += 5
            set_led(dev["id"], "green")
            data_list.append(data)
        else:
            health_score -= 5
            set_led(dev["id"], "orange")
            retry_list.append(dev)
        log_health_score(
            room_id=data["room_id"], state_change=health_score, battery=data["voltage"]
        )

    if retry_list:
        if DEBUG:
            print("Retrying failed connections...")
        for dev in retry_list:
            health_score = 0
            succes, data = get_rht_data(dev)
            if succes:
                health_score += 0
                set_led(dev["id"], "green")
                data_list.append(data)
            else:
                health_score -= 5
                set_led(dev["id"], "red")
            log_health_score(
                room_id=data["room_id"], state_change=health_score, battery=data["voltage"]
            )
    return data_list


def log_health_score(room_id, state_change, battery):
    """Store the state of a device in the database."""
    bat_hi = 3.2
    bat_lo = 2.2
    old_state = constants.get_health(room_id)
    if DEBUG:
        print(f"         battery level  = {battery} ")
    # LYWS02D devices do not report battery level.
    if not battery:
        battery = bat_lo - 0.01
    bat_state = (min(max(bat_lo, battery), bat_hi) - bat_lo) / (bat_hi - bat_lo) * 100.0
    state = min(bat_state, old_state) + state_change
    state = int(max(0, min(state, 100)))
    if state <= 25:
        set_led(room_id, "orange")
    if DEBUG:
        print(f"         previous state = {old_state}; new state = {state}")
    sql_health.queue({"health": state, "room_id": room_id, "name": constants.ROOMS[room_id]})


def get_rht_data(dev_dict):
    """Fetch data from a device.

    Args:
        dev_dict (dict)

    Returns:
        (bool)  to indicate success or failure to read a device's data
        (dict)  device's data; keys match fieldnames in the database
    """
    temperature = 0.0
    humidity = 0
    voltage = 0.0
    success = False
    t0 = time.time()
    try:
        client = dev_dict["device"]
        if DEBUG:
            print("")
            print(f"Fetching data from {dev_dict['mac']}")
            print("+------------------------------------")
        data = client.data
        if DEBUG:
            print(f"| Temperature       : {data.temperature}°C")
            print(f"| Humidity          : {data.humidity}%")
            print(f"| Battery           : {data.battery}% ({data.voltage}V)")
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
    except pyly.PyLyTimeout:
        err_date = dt.datetime.now()
        mf.syslog_trace(
            f"Timeout on {err_date.strftime(constants.DT_FORMAT)} "
            f"for room {dev_dict['id']} ({dev_dict['mac']}) ",
            syslog.LOG_CRIT,
            DEBUG,
        )
    except Exception as her:  # pylint: disable=W0703
        err_date = dt.datetime.now()
        mf.syslog_trace(
            f"*** While talking to room {dev_dict['id']} ({dev_dict['mac']}) error {her} "
            f"of type {type(her).__name__} occured on {err_date.strftime(constants.DT_FORMAT)}",
            syslog.LOG_CRIT,
            DEBUG,
        )
        # mf.syslog_trace(f"    {her}", syslog.LOG_DEBUG, DEBUG)
        mf.syslog_trace(traceback.format_exc(), syslog.LOG_DEBUG, DEBUG)
    if DEBUG:
        print(f"|              Time : {time.time() - t0:.2f} seconds")
        print("+------------------------------------")
    out_date = dt.datetime.now()  # time.strftime('%Y-%m-%dT%H:%M:%S')
    out_epoch = int(out_date.timestamp())

    if voltage in (0.0, None):
        success = False

    return success, {
        "sample_time": out_date.strftime(constants.DT_FORMAT),
        "sample_epoch": out_epoch,
        "room_id": dev_dict["id"],
        "temperature": temperature,
        "humidity": humidity,
        "voltage": voltage,
    }


def do_work_ac(dev_list):
    """Scan the devices to get current readings.
    Args:
        dev_list: list of device objects

    Returns:
        (list) containing dicts with data
    """
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
    """Fetch data from an AC device.

    Args:
        airco:  device object

    Returns:
        (bool)  to indicate success or failure to read a device's data
        (dict)  device's data; keys match fieldnames in the database
    """
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
            f"*** While talking to {airco['name']} error {her} of type"
            f" {type(her).__name__} occured on {err_date.strftime(constants.DT_FORMAT)}:",
            syslog.LOG_CRIT,
            DEBUG,
        )
        mf.syslog_trace(traceback.format_exc(), syslog.LOG_DEBUG, DEBUG)
    if DEBUG:
        print(f"+----------------Room {airco['name']} Data----")
        print(f"| T(airco)  : Inside      {ac_t_in:.2f} degC state = {ac_pwr}")
        print(f"|             Target >>>> {ac_t_tgt:.2f} degC  mode = {ac_mode}")
        print(f"|             Outside     {ac_t_out:.2f} degC")
        print(f"| compressor: {ac_cmp:.0f} ")
        print("+---------------------------------------------")
        print(f"{time.time() - t0:.2f} seconds\n")

    out_date = dt.datetime.now()  # time.strftime('%Y-%m-%dT%H:%M:%S')
    out_epoch = int(out_date.timestamp())

    return success, {
        "sample_time": out_date.strftime(constants.DT_FORMAT),
        "sample_epoch": out_epoch,
        "room_id": airco["name"],
        "ac_power": ac_pwr,
        "ac_mode": ac_mode,
        "temperature_ac": ac_t_in,
        "temperature_target": ac_t_tgt,
        "temperature_outside": ac_t_out,
        "cmp_freq": ac_cmp,
    }


def set_led(dev, colour):
    mf.syslog_trace(f"room {dev} is {colour}", False, DEBUG)

    in_dirfile = f"{APPROOT}/www/{colour}.png"
    out_dirfile = f'{constants.TREND["website"]}{dev}.png'
    try:
        shutil.copy(f"{in_dirfile}", out_dirfile)
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    # initialise logging
    syslog.openlog(ident=f'{MYAPP}.{MYID.split(".")[0]}', facility=syslog.LOG_LOCAL0)
    # set-up LEDs
    for _device in constants.DEVICES:
        set_led(_device["id"], "orange")
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

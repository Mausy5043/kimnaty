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

import numpy as np

import constants
import libdaikin
import mausy5043_common.funfile as mf
import mausy5043_common.libsignals as ml
import mausy5043_common.libsqlite3 as m3
import pylywsdxx as pyly  # noqa  # type: ignore

# fmt: off
parser = argparse.ArgumentParser(description="Execute the telemetry daemon.")
parser_group = parser.add_mutually_exclusive_group(required=True)
parser_group.add_argument("--start", action="store_true", help="start the daemon as a service")  # noqa
parser_group.add_argument("--debug", action="store_true", help="start the daemon in debugging mode")  # noqa
parser_group.add_argument("--debughw", action="store_true", help="start the daemon in hardware debugging mode")  # noqa
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

sql_health = m3.SqlDatabase(
    database=constants.HEALTH_UPDATE["database"],
    table=constants.HEALTH_UPDATE["sql_table"],
    insert=constants.HEALTH_UPDATE["sql_command"],
    debug=OPTION.debug,
)


def main():  # noqa: C901
    """Execute main loop."""
    killer = ml.GracefulKiller()

    # create an object for the database table for BT devices
    sql_db_rht = m3.SqlDatabase(
        database=constants.KIMNATY["database"],
        table=constants.KIMNATY["sql_table"],
        insert=constants.KIMNATY["sql_command"],
        debug=DEBUG,
    )

    # create an object for the database table for AC devices
    sql_db_ac = m3.SqlDatabase(
        database=constants.AC["database"],
        table=constants.AC["sql_table"],
        insert=constants.AC["sql_command"],
        debug=DEBUG,
    )

    # create an object for the management of the BT devices
    pylyman = pyly.PyLyManager(debug=DEBUG_HW)

    report_time = np.array([constants.KIMNATY["report_time"], constants.AC["report_time"]])
    cycle_time = np.array([constants.KIMNATY["cycle_time"], constants.AC["cycle_time"]])
    list_of_devices = constants.DEVICES
    if DEBUG:
        print(f"report_time : {report_time} s")
        print(list_of_devices)
    for bt_dev in list_of_devices:
        pylyman.subscribe_to(mac=bt_dev["mac"], name=bt_dev["name"])
    list_of_aircos = constants.AIRCO
    if DEBUG:
        print(list_of_aircos)
    for airco in list_of_aircos:
        airco["device"] = libdaikin.Daikin(airco["ip"])

    next_sample = np.array([time.time(), time.time()])
    next_report = report_time + time.time()
    while not killer.kill_now:
        # get RH/T data
        if time.time() > next_sample[0]:
            start_time = time.time()
            pylyman.update_all()
            if DEBUG:
                print(f">>> {time.time()-start_time:.1f} s to update {len(list_of_devices)} sensors")
            for device in list_of_devices:
                dev_qos, data_dict = get_rht_data(pylyman.get_state_of(device["name"]))
                sql_db_rht.queue(data_dict)
                record_qos(dev_qos, data_dict["name"])

            next_sample[0] = cycle_time[0] + start_time - (start_time % cycle_time[0])
        # get AC data
        if time.time() > next_sample[1]:
            start_time = time.time()
            ac_results = do_work_ac(list_of_aircos)
            # queue AC sample data
            if ac_results:
                for element in ac_results:
                    sql_db_ac.queue(element)
            if DEBUG:
                print(f" >>> Time to get AC results: {time.time() - start_time:.2f}")
            next_sample[1] = cycle_time[1] + start_time - (start_time % cycle_time[1])
        # report queued RH/T results
        if time.time() > next_report[0]:
            try:
                sql_db_rht.insert(method="replace")
                sql_health.insert(method="replace", index="room_id")
                next_report[0] = report_time[0] + time.time()
            except Exception as her:  # pylint: disable=W0703
                mf.syslog_trace(
                    f"*** While trying to insert data into the database  {type(her).__name__} {her} ",  # noqa: E501
                    syslog.LOG_CRIT,
                    DEBUG,
                )
                mf.syslog_trace(traceprint(traceback.format_exc()), syslog.LOG_ALERT, DEBUG)
                raise  # may be changed to pass if errors can be corrected.
        # report queued AC results
        if time.time() > next_report[1]:
            try:
                sql_db_ac.insert(method="replace")
                next_report[1] = report_time[1] + time.time()
            except Exception as her:  # pylint: disable=W0703
                mf.syslog_trace(
                    f"*** While trying to insert data into the database {type(her).__name__} {her} ",  # noqa: E501
                    syslog.LOG_CRIT,
                    DEBUG,
                )
                mf.syslog_trace(traceprint(traceback.format_exc()), syslog.LOG_ALERT, DEBUG)
                raise  # may be changed to pass if errors can be corrected.
        time.sleep(1.0)
    # report any still queued results
    sql_db_rht.insert(method="replace")
    sql_health.insert(method="replace", index="room_id")
    sql_db_ac.insert(method="replace")


def record_qos(dev_qos: int, room_id: str):
    """Scan the devices to get current readings.

    Args:
        dev_qos: QoS score of the device
        room_id: name of the device

    Returns:
        Nothing
    """
    set_led(room_id, "red")
    if dev_qos > 20:
        set_led(room_id, "orange")
    if dev_qos > 30:
        set_led(room_id, "green")
    log_health_score(room_id, dev_qos)


def log_health_score(room_id, state):
    """Store the state of a device in the database."""
    old_state = constants.get_health(room_id)
    if DEBUG:
        print(f"         previous state = {old_state}; new state = {state}")
    sql_health.queue({"health": state, "room_id": room_id, "name": constants.ROOMS[room_id]})


def get_rht_data(dev_dict):
    """Fetch data from a device.
{
        "mac": mac,             # MAC address provided by the client
        "name": name,           # (optional) device name provided by the client for easier identification
        "quality": 100,         # (int) 0...100, expresses the devices QoS
        "temperature": degC,    # (float) latest temperature
        "humidity": percent,    # (int) latest humidity
        "voltage": volts,       # (float) latest voltage
        "battery": percent,     # (float) current battery SoC
        "datetime": datetime,   # timestamp of when the above data was collected (datetime object)
        "epoch": UN*X epoch,    # timestamp of when the above data was collected (UNIX epoch)
        },

    Args:
        dev_dict (dict)

    Returns:
        (int)   to indicate the QoS of the device
        (dict)  device's data; keys match fieldnames in the database
    """
    temperature: float = dev_dict["temperature"]
    humidity: int = dev_dict["humidity"]
    voltage: float = dev_dict["voltage"]
    battery: float = dev_dict["battery"]
    qos: int = dev_dict["quality"]
    out_date = dev_dict["datetime"].strftime(constants.DT_FORMAT)
    out_epoch = dev_dict["epoch"]

    success = True
    if DEBUG:
        print("")
        print(f"Rewrapping data from {dev_dict['mac']} ({dev_dict['name']})")
        print(f"+------------------------------------------ {out_date} --")
        print(f"| Temperature       : {temperature}°C")
        print(f"| Humidity          : {humidity}%")
        print(f"| Battery           : {battery}% ({voltage}V)")
        print("+------------------------------------")

    # except BrokenPipeError:
    #     err_date = dt.datetime.now()
    #     mf.syslog_trace(
    #         f"BrokenPipeError on {err_date.strftime(constants.DT_FORMAT)}", syslog.LOG_CRIT, DEBUG
    #     )
    # except pyly.PyLyTimeout:
    #     err_date = dt.datetime.now()
    #     mf.syslog_trace(
    #         f"Timeout on {err_date.strftime(constants.DT_FORMAT)} "
    #         f"for room {dev_dict['id']} ({dev_dict['mac']}) ",
    #         syslog.LOG_CRIT,
    #         DEBUG,
    #     )
    # except Exception as her:  # pylint: disable=W0703
    #     err_date = dt.datetime.now()
    #     mf.syslog_trace(
    #         f"*** While talking to room {dev_dict['id']} ({dev_dict['mac']}) {type(her).__name__} {her} ",  # noqa: E501
    #         syslog.LOG_CRIT,
    #         DEBUG,
    #     )
    #     # mf.syslog_trace(f"    {her}", syslog.LOG_DEBUG, DEBUG)
    #     mf.syslog_trace(traceprint(traceback.format_exc()), syslog.LOG_DEBUG, DEBUG)

    return qos, {
        "sample_time": out_date,
        "sample_epoch": out_epoch,
        "room_id": dev_dict["name"],
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
        mf.syslog_trace(
            f"*** While talking to {airco['name']} {type(her).__name__} {her}",
            syslog.LOG_CRIT,
            DEBUG,
        )

        mf.syslog_trace(traceprint(traceback.format_exc()), syslog.LOG_DEBUG, DEBUG)
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
    out_dirfile = f'{constants.TREND["website"]}/{dev}.png'
    try:
        shutil.copy(f"{in_dirfile}", out_dirfile)
    except FileNotFoundError:
        pass


def traceprint(trace: str) -> str:
    received_lines: list[str] = trace.split("\n")
    filtered_lines: list[str] = []
    for line in received_lines:
        if line and line[0] == " ":
            if "File" in line:
                filtered_lines.append(line)
        else:
            filtered_lines.append(line)
    returned_lines: str = "\n".join(filtered_lines)
    return returned_lines


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

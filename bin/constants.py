#!/usr/bin/env python3

import os
import pprint as pp
import sqlite3 as s3
import subprocess  # nosec B404
import sys

import pandas as pd

# fmt: off

_MYHOME = os.environ["HOME"]
_DATABASE_FILENAME = "kimnaty.v2.sqlite3"
_DATABASE = f"/srv/rmt/_databases/kimnaty/{_DATABASE_FILENAME}"
_WEBSITE = "/run/kimnaty/site"
_HERE = os.path.realpath(__file__).split("/")  # ['', 'home', 'pi', 'kimnaty', 'bin', 'constants.py']
_HERE = "/".join(_HERE[0:-2])

ROOMS = dict()
BAT_HEALTH = dict()

if not os.path.isfile(_DATABASE):
    _DATABASE = f"/srv/databases/{_DATABASE_FILENAME}"
if not os.path.isfile(_DATABASE):
    _DATABASE = f"/srv/data/{_DATABASE_FILENAME}"
if not os.path.isfile(_DATABASE):
    _DATABASE = f"/mnt/data/{_DATABASE_FILENAME}"
if not os.path.isfile(_DATABASE):
    _DATABASE = f".local/{_DATABASE_FILENAME}"
    print("Searching for database in .local")
if not os.path.isfile(_DATABASE):
    _DATABASE = f"{_MYHOME}/.sqlite3/{_DATABASE_FILENAME}"
    print(f"Searching for database in {_MYHOME}/.sqlite3")
if not os.path.isfile(_DATABASE):
    print("Database is missing.")
    # _DATABASE_FILENAME = "unknown"
    # _DATABASE = None
    sys.exit(1)

DT_FORMAT = "%Y-%m-%d %H:%M:%S"

# The paths defined here must match the paths defined in include.sh
# $website_dir  and  $website_image_dir
TREND = {
    "database": _DATABASE,
    "sql_table_rht": "data",
    "sql_table_ac": "aircon",
    "website": _WEBSITE,
    "day_graph": f"{_WEBSITE}/img/kim_hours",
    "month_graph": f"{_WEBSITE}/img/kim_days",
    "year_graph": f"{_WEBSITE}/img/kim_months",
}

DEVICES = [
    {"mac": "A4:C1:38:A5:71:D0", "id": "0.1", "name": "woonkamer", "device": None},
    {"mac": "A4:C1:38:99:AC:4D", "id": "0.5", "name": "keuken", "device": None},
    {"mac": "A4:C1:38:6F:E7:CA", "id": "1.1", "name": "slaapkamer 1", "device": None},
    {"mac": "A4:C1:38:50:D7:2D", "id": "1.2", "name": "badkamer", "device": None},
    {"mac": "A4:C1:38:91:D9:47", "id": "1.3", "name": "slaapkamer 2", "device": None},
    {"mac": "A4:C1:38:59:9A:9B", "id": "1.4", "name": "slaapkamer 3", "device": None},
    {"mac": "A4:C1:38:76:59:43", "id": "2.1", "name": "zolder", "device": None},
    {"mac": "A4:C1:38:58:23:E1", "id": "2.2", "name": "slaapkamer 4", "device": None},
]

AIRCO = [
    {"name": "airco0", "ip": "192.168.2.30", "device": None},
    {"name": "airco1", "ip": "192.168.2.31", "device": None},
]

# Reading a LYWSD03 sensor takes 11.5 sec on average. You may get
# down to 6 seconds on a good day.
# `KIMNATY['report_time']` is determined by the number of devices
# to be interogated * 12 sec/device
# and allowing for all to misread every cycle.
# Also the aircos are read. Reading those takes on average 1 sec/AC.
# Here too, we allow for 1 misread.
_sample_time_per_device = 12.0 + 8.0
_sample_time_per_ac = 5.0
# Set a minimum pause time between scans
_pause_time = 30.0
_report_time = (
    (_sample_time_per_device * (len(DEVICES) * 2))
    + (_sample_time_per_ac * (len(AIRCO)))
    + _pause_time
)
# The minimum report_time is 900 seconds, to prevent unrealistic scantimes,
# high loads and battery drain.
_report_time = max(_report_time, 900.0)

KIMNATY = {
    "database": _DATABASE,
    "sql_command": (
        "INSERT INTO data ("
        "sample_time, sample_epoch, "
        "room_id, "
        "temperature, humidity, voltage "
        ") "
        "VALUES (?, ?, ?, ?, ?, ?)"
    ),
    "sql_table": "data",
    "report_time": _report_time,
    "cycles": 1,
    "samplespercycle": 1,
}

AC = {
    "database": _DATABASE,
    "sql_command": (
        "INSERT INTO aircon ("
        "sample_time, sample_epoch, "
        "room_id, "
        "ac_power, ac_mode,"
        "temperature_ac, temperature_target, temperature_outside, "
        "cmp_freq) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    ),
    "sql_table": "aircon",
}

# Example: UPDATE rooms SET health=40 WHERE room_id=0.1;
HEALTH_UPDATE = {
    "database": _DATABASE,
    "sql_command": "INSERT INTO rooms (room_id, name, health) VALUES (?, ?, ?)",
    "sql_table": "rooms",
}

_health_query = "SELECT * FROM rooms;"


def get_health(room_id):
    _health = 0
    with s3.connect(_DATABASE) as _con:
        _table_data = pd.read_sql_query(_health_query, _con, index_col="room_id").to_dict()
    try:
        _health = _table_data["health"][room_id]
    except KeyError:
        print(f"*** KeyError when retrieving health for room {room_id}")
        print(_table_data)
    return _health


def get_kimnaty_version() -> str:
    """Retrieve information of current version of kimnaty.

    Returns:
        versionstring
    """
    # git log -n1 --format="%h"
    # git --no-pager log -1 --format="%ai"
    args = ["git", "log", "-1", "--format='%h'"]
    _exit_h = (
        subprocess.check_output(args, cwd=_HERE, shell=False, encoding="utf-8")  # nosec B603
        .strip("\n")
        .strip("'")
    )
    args[3] = "--format='%ai'"
    _exit_ai = (
        subprocess.check_output(args, cwd=_HERE, shell=False, encoding="utf-8")  # nosec B603
        .strip("\n")
        .strip("'")
    )
    return f"{_exit_h}  -  {_exit_ai}"


def get_pypkg_version(package) -> str:
    # pip list | grep bluepy3
    args = ["pip", "list"]
    _exit_code = (
        subprocess.check_output(args, shell=False, encoding="utf-8", stderr=subprocess.DEVNULL)  # nosec B603
        .strip("\n")
        .strip("'")
    ).split("\n")
    for element in _exit_code:
        element_list = element.split()
        if element_list[0] == package:
            return element_list[1]
    return f"unknown package {package}"


def get_btctl_version():
    # bluetoothctl version
    args = ["bluetoothctl", "version"]
    try:
        _exit_code = (subprocess.check_output(args, shell=False, encoding="utf-8", )  # nosec B603
                      .strip("\n")
                      .strip("'")
                      ).split()
    except FileNotFoundError:
        return "not installed"
    return f"{_exit_code[1]}"


def get_helper_version():
    helper_list = find_all("bluepy3-helper", "/")
    for helper in helper_list:
        args = [helper, "version"]
        try:
            _exit_code = (
                subprocess.check_output(args, shell=False, encoding="utf-8", stderr=subprocess.STDOUT)  # nosec B603
                .strip("\n")
                .strip("'")
            ).split()
        except subprocess.CalledProcessError as exc:
            _exit_code = exc.output.split('\n')[0]
    return _exit_code


def find_all(name, path):
    result = []
    for root, dirs, files in os.walk(path):
        if name in files:
            result.append(os.path.join(root, name))
    return result


if _DATABASE:
    with s3.connect(_DATABASE) as _con:
        _ROOMS_TBL = pd.read_sql_query(_health_query, _con, index_col="room_id").to_dict()
    try:
        ROOMS = _ROOMS_TBL["name"]
    except KeyError:
        print("*** KeyError when retrieving ROOMS")
        print(_ROOMS_TBL)
        raise
    try:
        BAT_HEALTH = _ROOMS_TBL["health"]
    except KeyError:
        print("*** KeyError when retrieving BAT_HEALTH")
        print(_ROOMS_TBL)
        raise

# fmt: on

if __name__ == "__main__":
    print(f"home              = {_MYHOME}")
    print(f"database location = {_DATABASE}")
    print(f"rooms             =\n{pp.pformat(ROOMS, indent=20)}")
    print(f"battery health    =\n{pp.pformat(BAT_HEALTH, indent=20)}")
    print("")
    print(f"bluetoothctl      = {get_btctl_version()}")
    print(f"bluepy3-helper    = {get_helper_version()}")
    print(f"bluepy3           = {get_pypkg_version('bluepy3')}")
    print(f"pylywsdxx         = {get_pypkg_version('pylywsdxx')}")
    print(f"kimnaty (me)      = {get_kimnaty_version()}")

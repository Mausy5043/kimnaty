#!/usr/bin/env python3

import json
import os
import pprint as pp
import sqlite3 as s3
import subprocess
import sys
import time

import pandas as pd
from pandas.errors import DatabaseError
from sh import CommandNotFound
import sh

# fmt: off
# define paths
_MYHOME = os.environ["HOME"]
_DATABASE_FILENAME = "kimnaty.v2.sqlite3"
_DATABASE: str = f"/srv/rmt/_databases/kimnaty/{_DATABASE_FILENAME}"
_HERE = os.path.realpath(__file__).split("/")
# example: HERE = ['', 'home', 'pi', 'kimnaty', 'bin', 'constants.py']
_HERE = "/".join(_HERE[0:-2])
_OPTION_OVERRIDE_FILE = f"{_MYHOME}/.config/kimnaty.json"
_WEBSITE = "/run/kimnaty/site/img"

if not os.path.isfile(_DATABASE):
    _DATABASE = f"/srv/databases/{_DATABASE_FILENAME}"
if not os.path.isfile(_DATABASE):
    _DATABASE = f"/srv/data/{_DATABASE_FILENAME}"
if not os.path.isfile(_DATABASE):
    _DATABASE = f"/mnt/data/{_DATABASE_FILENAME}"
if not os.path.isfile(_DATABASE):
    _DATABASE = f".local/{_DATABASE_FILENAME}"
    print(f"Searching for {_DATABASE}")
if not os.path.isfile(_DATABASE):
    _DATABASE = f"{_MYHOME}/.sqlite3/kimnaty/{_DATABASE_FILENAME}"
    print(f"Searching for {_DATABASE}")
if not os.path.isfile(_DATABASE):
    print("Database is missing.")
    # _DATABASE_FILENAME = "unknown"
    # _DATABASE = None
    sys.exit(1)

if not os.path.isdir(_WEBSITE):
    print("Graphics will be diverted to /tmp")
    _WEBSITE = "/tmp"   # nosec B108

DT_FORMAT = "%Y-%m-%d %H:%M:%S"

ROOMS = {}
BAT_HEALTH = {}
OPTION_OVERRIDE = {}

if os.path.isfile(_OPTION_OVERRIDE_FILE):
    with open(_OPTION_OVERRIDE_FILE, "r", encoding="utf-8") as j:
        # order of overrides:
        # 1. hardcoded default
        # 2. OPTION_OVERRIDE setting
        # 3. CLI OPTION setting
        OPTION_OVERRIDE = json.load(j, parse_float=float, parse_int=int)

# The paths defined here must match the paths defined in include.sh
# $website_dir  and  $website_image_dir
TREND = {
    "database": _DATABASE,
    "sql_table_rht": "data",
    "sql_table_ac": "aircon",
    "website": _WEBSITE,
    "day_graph": f"{_WEBSITE}/kim_hours",
    "month_graph": f"{_WEBSITE}/kim_days",
    "year_graph": f"{_WEBSITE}/kim_months",
    "option_hours": OPTION_OVERRIDE.get('trend', {}).get('hours', 84),  # 3.5 days
    "option_days": OPTION_OVERRIDE.get('trend', {}).get('days', 77),  # 2.5 months
    "option_months": OPTION_OVERRIDE.get('trend', {}).get('months', 38),  # 3 years & 2 months
    "option_outside": OPTION_OVERRIDE.get('trend', {}).get('outside', False),
}

DEVICES = [
    {"mac": "A4:C1:38:59:9A:9B", "room_id": "0.1", "name": "woonkamer", "device": None},
    {"mac": "A4:C1:38:99:AC:4D", "room_id": "0.5", "name": "keuken", "device": None},
    {"mac": "A4:C1:38:6F:E7:CA", "room_id": "1.1", "name": "slaapkamer 1", "device": None},
    {"mac": "A4:C1:38:50:D7:2D", "room_id": "1.2", "name": "slaapkamer 2", "device": None},
    {"mac": "A4:C1:38:91:D9:47", "room_id": "1.3", "name": "slaapkamer 3", "device": None},
    {"mac": "A4:C1:38:A5:71:D0", "room_id": "1.4", "name": "badkamer", "device": None},
    {"mac": "A4:C1:38:76:59:43", "room_id": "2.1", "name": "zolder", "device": None},
    {"mac": "A4:C1:38:58:23:E1", "room_id": "2.2", "name": "slaapkamer 4", "device": None},
]

# - sample_time = time to get one reading from a device
# - cycle_time = time between samples

# Reading a LYWSD03 sensor takes 11.5 sec on average. You may get
# down to 6 seconds on a good day.
_sample_time_lyw = 11.5 + 8.0
# and allowing for all to misread every cycle.
_sample_time_lyws = _sample_time_lyw * len(DEVICES) * 2
# The cycle time is about 1200 seconds, to prevent unrealistic scantimes,
# high loads and battery drain.
_cycle_time = 2100.0

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
    "cycle_time": _cycle_time,
    "aggregate": "raw",
}

AIRCO = [
    {"name": "airco0", "ip": "192.168.2.30", "device": None},
    {"name": "airco1", "ip": "192.168.2.31", "device": None},
]

# Also the aircos are read. Reading those takes on average 2 sec/AC.
# Here too, we allow for 1 misread.
_sample_time_ac = 5.0
_sample_time_acs = _sample_time_ac * len(AIRCO)
# Set a minimum pause time between scans
_cycle_time_ac = 120.0

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
    "cycle_time": _cycle_time_ac,
    "aggregate": "avg",
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
    # fixme: database may be locked
    with s3.connect(_DATABASE) as conn:
        _table_data = pd.read_sql_query(_health_query, conn, index_col="room_id").to_dict()
    try:
        _health = _table_data["health"][room_id]
    except KeyError:
        print(f"*** KeyError when retrieving health for room {room_id}")
        print(_table_data)
    return _health


def get_app_version() -> str:
    """Retrieve information of current version of kimnaty.

    Returns:
        versionstring
    """
    # git log -n1 --format="%h"
    # git --no-pager log -1 --format="%ai"
    # git log -n1 --format="%h"
    # git --no-pager log -1 --format="%ai"
    git_args = ["-C", f"{_HERE}", "--no-pager", "log", "-1", "--format='%h'"]
    try:
        _exit_h = sh.git(git_args).strip("\n").strip("'")
    except CommandNotFound as e:
        print(f"Error executing command: {e}")
        _exit_h = None
    git_args[5] = "--format='%ai'"
    _exit_ai = sh.git(git_args).strip("\n").strip("'")
    return f"{_exit_h}  -  {_exit_ai}"


def get_pypkg_version(package) -> str:
    # pip list | grep bluepy3
    args = ["list"]
    try:
        _exit_code = sh.pip(args).split("\n")  # type: ignore
    except CommandNotFound as e:
        print(f"Error executing command: {e}")
        _exit_code = [""]
    for element in _exit_code:
        if element:
            element_list = element.split()
            if element_list[0] == package:
                return element_list[1]
    return "not installed"


def get_btctl_version():
    # bluetoothctl version
    args = ["version"]
    try:
        _exit_code = sh.bluetoothctl(args).strip("\n").strip("'").split()  # type: ignore
    except CommandNotFound as e:
        print(f"Error executing command: {e}")
        return "not installed"
    return f"{_exit_code[1]}"


def get_helper_version() -> str:
    wait_string = "Please wait while searching for helper..."
    _exit_code = "not installed"
    print(wait_string, end="\r")
    helper_list = find_all("bluepy3-helper", "/")
    print(" " * len(wait_string), end="\r")
    for helper in helper_list:
        args = [helper, "version"]
        try:
            # bluepy3_helper will print its version and then return an error
            # because 'version' is not a valid parameter value.
            _: list[str] = (
                subprocess.check_output(args, shell=False, encoding="utf-8", stderr=subprocess.STDOUT)  # noqa # nosec B603
                .strip("\n")
                .strip("'")
            ).split()
        except subprocess.CalledProcessError as exc:
            _exit_code = str(exc.output.split("\n")[0])
            _exit_code = _exit_code.replace("# ", "")
        # try:
        #     _exit_code = sh.sh(args).strip("\n").strip("'")
        except CommandNotFound as e:
            print(f"Error executing command: {e}")
            _exit_code = "not installed"
    return _exit_code
# fmt: on


def find_all(name, path):
    result = []
    for root, _, files in os.walk(path):
        if name in files:
            result.append(os.path.join(root, name))
    return result


if _DATABASE:
    _locked = True
    while _locked:
        with s3.connect(_DATABASE) as _con:
            try:
                _ROOMS_TBL = pd.read_sql_query(_health_query, _con, index_col="room_id").to_dict()
                _locked = False
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
            except DatabaseError:
                # database is locked
                # print("database is locked; waiting...")
                time.sleep(10.0)


# fmt: on


if __name__ == "__main__":
    print("")
    print(f"home              = {_MYHOME}")
    print(f"database location = {_DATABASE}")
    print(f"devices           =\n{pp.pformat(DEVICES, indent=10)}")
    print(f"rooms (DB)        =\n{pp.pformat(ROOMS, indent=20)}")
    print(f"battery health    =\n{pp.pformat(BAT_HEALTH, indent=20)}")
    print("")
    print(f"user options      =\n{pp.pformat(OPTION_OVERRIDE, indent=10, width=1)}")
    print(f"trend options     =\n{pp.pformat(TREND, indent=10, width=1)}")
    print("")
    print(f"bluetoothctl      = {get_btctl_version()}")
    print(f"bluepy3-helper    = {get_helper_version()}")
    print(f"bluepy3           = {get_pypkg_version('bluepy3')}")
    print(f"pylywsdxx         = {get_pypkg_version('pylywsdxx')}")
    print(f"kimnaty (me)      = {get_app_version()}")

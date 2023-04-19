#!/usr/bin/env python3

import os
import sqlite3 as s3
import sys

import pandas as pd

_MYHOME = os.environ["HOME"]
_DATABASE_FILENAME = "kimnaty.v2.sqlite3"
_DATABASE = f"/srv/rmt/_databases/kimnaty/{_DATABASE_FILENAME}"
_WEBSITE = "/run/kimnaty/site"

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
    sys.exit(1)

DT_FORMAT = "%Y-%m-%d %H:%M:%S"

# The paths defined here must match the paths defined in constants.sh
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
    ["A4:C1:38:A5:71:D0", "0.1"],
    ["A4:C1:38:99:AC:4D", "0.5"],
    ["A4:C1:38:6F:E7:CA", "1.1"],
    ["A4:C1:38:50:D7:2D", "1.2"],
    ["A4:C1:38:91:D9:47", "1.3"],
    ["A4:C1:38:59:9A:9B", "1.4"],
    ["A4:C1:38:76:59:43", "2.1"],
    ["A4:C1:38:58:23:E1", "2.2"],
]

AIRCO = [
    {"name": "airco0", "ip": "192.168.2.30", "device": None},
    {"name": "airco1", "ip": "192.168.2.31", "device": None},
]

# Reading a LYWSD03 sensor takes 11.5 sec on average.
# `KIMNATY['report_time']` is determined by the number of devices to be interogated * 12 sec/device
# and allowing for all to misread every cycle.
# Also the aircos are read. Reading those takes on average 1 sec/AC. Here too, we allow for 1 misread.
_sample_time_per_device = 12.0 + 8.0
_sample_time_per_ac = 5.0
# Set a minimum pause time between scans
_pause_time = 30.0
_report_time = (
    (_sample_time_per_device * (len(DEVICES) * 2))
    + (_sample_time_per_ac * (len(AIRCO)))
    + _pause_time
)
# The minimum report_time is 600 seconds, to prevent unrealistic scantimes, high loads and battery drain.
_report_time = max(_report_time, 1000.0)

KIMNATY = {
    "database": _DATABASE,
    "sql_command": "INSERT INTO data ("
    "sample_time, sample_epoch, "
    "room_id, "
    "temperature, humidity, voltage "
    ") "
    "VALUES (?, ?, ?, ?, ?, ?)",
    "sql_table": "data",
    "report_time": _report_time,
    "cycles": 1,
    "samplespercycle": 1,
}

AC = {
    "database": _DATABASE,
    "sql_command": "INSERT INTO aircon ("
    "sample_time, sample_epoch, "
    "room_id, "
    "ac_power, ac_mode,"
    "temperature_ac, temperature_target, temperature_outside, "
    "cmp_freq) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    "sql_table": "aircon",
}

# Example: UPDATE rooms SET health=40 WHERE room_id=0.1;
HEALTH_UPDATE = {
    "database": _DATABASE,
    "sql_command": "UPDATE rooms SET health = %s WHERE room_id = %s",
    "sql_table": "rooms",
}


_s3_query = "SELECT * FROM rooms;"


def get_health(room_id):
    # _s3_query = "SELECT * FROM rooms;"
    with s3.connect(_DATABASE) as _con:
        _table_data = pd.read_sql_query(_s3_query, _con, index_col="room_id").to_dict()
    try:
        _health = _table_data["health"][room_id]
    except KeyError:
        print(f"*** KeyError when retrieving health for room {room_id}")
        print(_table_data)
    return _health


with s3.connect(_DATABASE) as _con:
    _ROOMS_TBL = pd.read_sql_query(_s3_query, _con, index_col="room_id").to_dict()
try:
    ROOMS = _ROOMS_TBL["name"]
    BAT_HEALTH = _ROOMS_TBL["health"]
except KeyError:
    print("*** KeyError when retrieving ROOMS or BAT_HEALTH")
    print(_ROOMS_TBL)


if __name__ == "__main__":
    print(f"home              = {_MYHOME}")
    print(f"database location = {_DATABASE}")
    print("")
    print(f"rooms             = {ROOMS}")
    print(f"battery health    = {BAT_HEALTH}")

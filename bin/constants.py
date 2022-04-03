#!/usr/bin/env python3

import os
import sys
import pandas as pd
import sqlite3 as s3

_MYHOME = os.environ["HOME"]
_DATABASE = '/srv/databases/kimnaty.sqlite3'

if not os.path.isfile(_DATABASE):
    _DATABASE = '/srv/data/kimnaty.sqlite3'
if not os.path.isfile(_DATABASE):
    _DATABASE = '/mnt/data/kimnaty.sqlite3'
if not os.path.isfile(_DATABASE):
    _DATABASE = f'.local/kimnaty.sqlite3'
if not os.path.isfile(_DATABASE):
    _DATABASE = f'{_MYHOME}/.sqlite3/kimnaty.sqlite3'
if not os.path.isfile(_DATABASE):
    print("Database is missing.")
    sys.exit(1)

TREND = {'database': _DATABASE,
         'sql_table_rht': "data",
         'sql_table_ac': "aircon",
         'day_graph': '/tmp/kimnaty/site/img/kim_hours',
         'month_graph': '/tmp/kimnaty/site/img/kim_days',
         'year_graph': '/tmp/kimnaty/site/img/kim_months'
         }

DEVICES = [['A4:C1:38:99:AC:4D', '0.6']
           ]

AIRCO = [{'name': 'airco0',
          'ip': '192.168.2.30',
          'device': None
          },
         {'name': 'airco1',
          'ip': '192.168.2.31',
          'device': None
          }
         ]

# Reading a LYWSD03 sensor takes 11.5 sec on average.
# `KIMNATY['report_time']` is determined by the number of devices to be interogated * 12 sec/device
# and allowing for 2 misreads every cycle.
# Also the two aircos are read. Reading those takes on average 1 sec/AC. Here too, we allow for 1 misread.
sample_time_per_device = 12.0
sample_time_per_ac = 1.0
report_time = (sample_time_per_device * (len(DEVICES) + 2)) + (sample_time_per_ac * (len(AIRCO) + 1))
# The minimum report_time is 60 seconds, to prevent unrealistic scantimes, high loads and battery drain.
if report_time < 60.0:
    report_time = 60.0

KIMNATY = {'database': _DATABASE,
           'sql_command': "INSERT INTO data ("
                          "sample_time, sample_epoch, "
                          "room_id, "
                          "temperature, humidity, voltage "
                          ") "
                          "VALUES (?, ?, ?, ?, ?, ?)",
           'sql_table': "data",
           'report_time': report_time,
           'cycles': 1,
           'samplespercycle': 1
           }

AC = {'database': _DATABASE,
      'sql_command': "INSERT INTO aircon ("
                     "sample_time, sample_epoch, "
                     "room_id, "
                     "ac_power, ac_mode,"
                     "temperature_ac, temperature_target, temperature_outside, "
                     "cmp_freq) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
      'sql_table': "aircon",
      }



_s3_query = f"SELECT * FROM rooms;"
with s3.connect(_DATABASE) as _con:
    ROOMS = pd.read_sql_query(_s3_query,
                              _con,
                              index_col='room_id'
                              )
try:
    ROOMS = ROOMS.to_dict()['name']
except KeyError:
    print("*** KeyError when retrieving ROOMS")
    print(ROOMS.to_dict())

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
         'sql_table': "data",
         'day_graph': '/tmp/kimnaty/site/img/kim_hours',
         'month_graph': '/tmp/kimnaty/site/img/kim_days',
         'year_graph': '/tmp/kimnaty/site/img/kim_months'
         }

KIMNATY = {'database': _DATABASE,
           'sql_command': "INSERT INTO data ("
                          "sample_time, sample_epoch, "
                          "room_id, "
                          "temperature, humidity, voltage "
                          ") "
                          "VALUES (?, ?, ?, ?, ?, ?)",
           'sql_table': "data",
           'report_time': 300,
           'cycles': 1,
           'samplespercycle': 1
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

#!/usr/bin/env python3

import os
import sys

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
         'day_graph': '/tmp/kimnaty/site/img/kim_pastday',
         'month_graph': '/tmp/kimnaty/site/img/kim_pastmonth',
         'year_graph': '/tmp/kimnaty/site/img/kim_pastyear'
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

DEVICES = [['A4:C1:38:99:AC:4D', '0.1.0'],
           ['A4:C1:38:99:AC:4D', '0.1.1']
           ]

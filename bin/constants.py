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

BATTERY = {'database': _DATABASE,
           'graph_file': ".local/graph.png"
           }

TREND = {'database': _DATABASE,
         'day_graph': '/tmp/kimnaty/site/img/kim_pastday.png',
         'month_graph': '/tmp/kimnaty/site/img/kim_pastmonth.png',
         'year_graph': '/tmp/kimnaty/site/img/kim_pastyear.png',
         'vsyear_graph': '/tmp/kimnaty/site/img/kim_vs_year.png',
         'yg_vs_month': '/tmp/kimnaty/site/img/kim_vs_month.png',
         'yg_gauge': '/tmp/kimnaty/site/img/kim_gauge.png'
         }

KIMNATY = {'database': _DATABASE,
           'sql_command': "INSERT INTO kimnaty ("
                          "sample_time, sample_epoch, "
                          "T1in, T2in, powerin, "
                          "T1out, T2out, powerout, "
                          "tarif, swits"
                          ") "
                          "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
           'sql_table': "kimnaty",
           'report_time': 600,
           'cycles': 1,
           'samplespercycle': 58
           }

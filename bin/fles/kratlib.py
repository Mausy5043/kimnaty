#!/usr/bin/env python3
"""Common functions for Flask webUI"""

import json
import os
import sys
import sqlite3
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
import constants  # noqa


def initial_state():
    """
    Set the factory settings for the application.
    The settings are stored in a dictionary.
    """
    defstate = dict()

    return defstate


class Fles:
    def __init__(self):
        # app info :
        # path to this file as a list of elements
        self.HERE = os.path.realpath(__file__).split('/')
        self.MYLEVEL = 4  # kimnaty =1, bin =2, fles =3
        # # element that contains the appname (given the location of this file)
        # self.MYAPP = self.HERE[-self.MYLEVEL]
        # # absolute path to the app's root
        self.MYROOT = "/".join(self.HERE[0:-self.MYLEVEL])
        # self.NODE = os.uname()[1]  # name of the host
        # self.ROOM_ID = self.NODE[-2:]  # inferred room-id

        self.DATABASE = constants.KIMNATY['database']
        self.CONFIG = f'{self.MYROOT}/.config/kimdata.json'
        self.req_state = dict()
        self.ctrl_state = dict()
        self.load_state()

    def get_latest_data(self, fields):
        """Retrieve the most recent datapoints from the database."""
        db_con = sqlite3.connect(self.DATABASE)
        with db_con:
            db_cur = db_con.cursor()
            db_cur.execute(f"SELECT {fields} FROM kimnaty \
                             WHERE sample_epoch = (SELECT MAX(sample_epoch) \
                                                   FROM kimnaty) \
                             ;")
            db_data = db_cur.fetchall()
        return list(db_data[0])

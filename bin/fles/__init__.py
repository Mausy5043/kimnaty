#!/usr/bin/env python3

from flask import Flask

app = Flask(__name__)

from fles import state  # noqa
from fles import kratlib  # noqa

#!/usr/bin/env python3

import argparse

import pylywsdxx as pyly  # noqa

parser = argparse.ArgumentParser()
parser.add_argument("mac", help="MAC address of LYWSD03 device", nargs="+")
args = parser.parse_args()

for mac in args.mac:
    try:
        device = pyly.Lywsd03(mac=mac, debug=True)
    except Exception as e:  # pylint: disable=W0703
        print(e)

    try:
        print(f"Fetching data from {mac}")
        data = device.data
        print(f"Temperature       : {data.temperature}°C")
        print(f"Humidity          : {data.humidity}%")
        print(f"Battery           : {data.battery}% ({data.voltage}V)")
        print()
    except Exception as e:  # pylint: disable=W0703
        print(e)

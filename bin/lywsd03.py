#!/usr/bin/env python3

import argparse
import lywsd03mmc
import time

parser = argparse.ArgumentParser()
parser.add_argument('mac', help='MAC address of LYWSD03 device', nargs='+')
args = parser.parse_args()

for mac in args.mac:
    try:
        client = lywsd03mmc.Lywsd03mmcClient(mac)
    except Exception as e:
        print(e)

    try:
        print(f'Fetching data from {mac}')
        data = client.data
        print(f'Temperature       : {data.temperature}°C')
        print(f'Humidity          : {data.humidity}%')
        print(f'Battery           : {data.battery}% ({data.voltage}V)')
        print()
    except Exception as e:
        print(e)

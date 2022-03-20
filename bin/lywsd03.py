#!/usr/bin/env python3

import argparse
from datetime import datetime
import lywsd03mmc

parser = argparse.ArgumentParser()
parser.add_argument('mac', help='MAC address of LYWSD03 device', nargs='+')
args = parser.parse_args()

for mac in args.mac:
    try:
        client = lywsd03mmc.Lywsd03mmcClient(mac)
        print(f'Fetching data from {mac}')
        data = client.data
        print(f'Temperature       : {data.temperature}°C')
        print(f'Humidity          : {data.humidity}%')
        print(f'Battery           : {data.battery}%')
        print(f'Device start time : {client.start_time}')
        print()
    except Exception as e:
        print(e)

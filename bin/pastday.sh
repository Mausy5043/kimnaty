#!/bin/bash

# query hourly totals for a period of two days and trend them

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)

pushd "${HERE}" >/dev/null || exit 1
    ./trend.py --days 0 &
    wait
popd >/dev/null || exit

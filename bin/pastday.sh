#!/bin/bash

# query hourly totals for a period of two days and trend them

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)

pushd "${HERE}" >/dev/null || exit 1
    # shellcheck disable=SC1091
    source ./include.sh
    if [ ! -d "${website_image_dir}" ]; then
        boot_kimnaty
    fi
    ./trend.py --hours 0
popd >/dev/null || exit

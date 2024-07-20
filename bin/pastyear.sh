#!/bin/bash

# query monthly totals for a period of n years

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)

pushd "${HERE}" >/dev/null || exit 1
    # shellcheck disable=SC1091
    source ./include.sh
    # shellcheck disable=SC2154
    if [ ! -d "${website_image_dir}" ]; then
        boot_kimnaty
    fi
    ./trend.py --months 0
popd >/dev/null || exit

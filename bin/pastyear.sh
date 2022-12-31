#!/bin/bash

# query monthly totals for a period of n years

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)

pushd "${HERE}" >/dev/null || exit 1
    ./trend.py --months 0
popd >/dev/null || exit

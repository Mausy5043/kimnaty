#!/bin/bash

# Use stop.sh to stop all daemons in one go
# You can use update.sh to get everything started again.

HERE=$(cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd)

pushd "${HERE}" || exit 1
    # shellcheck disable=SC1091
    source ./bin/constants.sh

    sudo systemctl stop kimnaty.fles.service

    sudo systemctl stop kimnaty.kimnaty.service

    sudo systemctl stop kimnaty.trend.day.timer
    sudo systemctl stop kimnaty.trend.month.timer
    sudo systemctl stop kimnaty.trend.year.timer
    sudo systemctl stop kimnaty.update.timer
popd || exit

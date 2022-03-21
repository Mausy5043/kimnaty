#!/bin/bash

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)

pushd "${HERE}" || exit 1
    # shellcheck disable=SC1091
    source ./bin/constants.sh

    echo
    echo -n "Started UNinstalling ${app_name} on "
    date
    echo

    # allow user to abort
    sleep 10

    ./stop.sh

    sudo systemctl disable kimnaty.fles.service
    sudo systemctl disable kimnaty.bluepy-helper-killer.service

    sudo systemctl disable kimnaty.kimnaty.service

    sudo systemctl disable kimnaty.trend.day.timer
    sudo systemctl disable kimnaty.trend.month.timer
    sudo systemctl disable kimnaty.trend.year.timer
    sudo systemctl disable kimnaty.update.timer

popd || exit

echo
echo "*********************************************************"
echo -n "Finished UNinstallation of ${app_name} on "
date
echo

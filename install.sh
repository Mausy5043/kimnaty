#!/bin/bash

install_package() {
    # See if packages are installed and install them.
    package=$1
    echo "*********************************************************"
    echo "* Requesting ${package}"
    status=$(dpkg -l | awk '{print $2}' | grep -c -e "^${package}$")
    if [ "${status}" -eq 0 ]; then
        echo "* Installing ${package}"
        echo "*********************************************************"
        sudo apt-get -yqV install "${package}"
    else
        echo "* Already installed !!!"
        echo "*********************************************************"
    fi
    echo
}

getfilefromserver() {
    file="${1}"
    mode="${2}"

    if [ ! -f "${HOME}/${file}" ]; then
        cp -rvf "/srv/config/${file}" "${HOME}/.config/"
        chmod "${mode}" "${HOME}/.config/${file}"
    fi
}

# ME=$(whoami)
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)
# MINIT=$(echo $RANDOM/555 | bc)

required_commonlibversion="1.0.0"
commonlibbranch="v1_0"

pushd "${HERE}" || exit 1
    # shellcheck disable=SC1091
    source ./bin/constants.sh
popd || exit 1

echo
# shellcheck disable=SC2154
echo -n "Started installing ${app_name} on "
date
echo
# echo "MINIT = ${minit}"

sudo apt-get update
# Python3 package and associates
install_package "python3"
install_package "build-essential"
install_package "python3-dev"
install_package "python3-pip"
install_package "libglib2.0-dev"
# Support for matplotlib & numpy needs to be installed seperately
install_package "libatlas-base-dev"
install_package "libxcb1"
# install_package "libpng16-16"
# install_package "libjpeg62"
install_package "libopenjp2-7"
install_package "libtiff5"
## install_package "libfreetype6-dev"
## install_package "libjpeg-dev"
# install_package "python3-scipy"

# SQLite3 support (incl python3)
install_package "sqlite3"

# required for hardware support (Bluetooth)
sudo addgroup --gid 112 bluetooth
sudo rm /etc/modprobe.d/dietpi-disable_bluetooth.conf
sudo sed -i /^[[:blank:]]*dtoverlay=disable-bt/d /boot/config.txt
install_package "pi-bluetooth"
install_package "bluetooth"
# install_package "pybluez"
install_package "bluez"
sudo addgroup --gid 112 bluetooth
sudo usermod -aG bluetooth pi

echo
echo "*********************************************************"
echo
python3 -m pip install --upgrade pip setuptools wheel
pushd "${HERE}" || exit 1
    python3 -m pip install -r requirements.txt
    python3 -m pip uninstall -y bluepy
    python3 -m pip install "git+https://github.com/Mausy5043/bluepy@kimnaty#egg=bluepy"
    echo
    echo -n "Installed: "
    python3 -m pip list | grep bluepy
popd || exit 1

commonlibversion=$(python3 -m pip freeze | grep mausy5043 | cut -c 26-)
if [ "${commonlibversion}" != "${required_commonlibversion}" ]; then
    echo
    echo "*********************************************************"
    echo "Install common python functions..."
    python3 -m pip uninstall -y mausy5043-common-python
    python3 -m pip install "git+https://gitlab.com/mausy5043-installer/mausy5043-common-python.git@${commonlibbranch}#egg=mausy5043-common-python"
    echo
    echo -n "Installed: "
    python3 -m pip list | grep mausy5043
    echo
fi

pushd "${HERE}" || exit 1
    # To suppress git detecting changes by chmod:
    git config core.fileMode false
    # set the branch
    if [ ! -e "${HOME}/.${app_name}.branch" ]; then
        echo "main" >"${HOME}/.${app_name}.branch"
    fi
    chmod -x ./services/*

    # install services and timers
    sudo cp ./services/*.service /etc/systemd/system/
    sudo cp ./services/*.timer /etc/systemd/system/
    #
    sudo systemctl daemon-reload
    #
    sudo systemctl enable kimnaty.trend.day.timer &
    sudo systemctl enable kimnaty.trend.month.timer &
    sudo systemctl enable kimnaty.trend.year.timer &
    sudo systemctl enable kimnaty.update.timer &

    sudo systemctl enable kimnaty.fles.service &
    sudo systemctl enable kimnaty.bluepy-helper-killer.service &
    sudo systemctl enable kimnaty.kimnaty.service &
    wait



    sudo systemctl start kimnaty.trend.day.timer
    sudo systemctl start kimnaty.trend.month.timer
    sudo systemctl start kimnaty.trend.year.timer
    sudo systemctl start kimnaty.bluepy-helper-killer.service
    sudo systemctl start kimnaty.update.timer # this will also start the daemon!

# services are started by the update script:
#    sudo systemctl start kimnaty.kimnaty.service
#    sudo systemctl start kimnaty.fles.service

popd || exit 1

echo
echo "*********************************************************"
echo -n "Finished installation of ${app_name} on "
date
echo

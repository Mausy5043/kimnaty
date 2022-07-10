#!/usr/bin/env bash

# shellcheck disable=SC2034
app_name="kimnaty"
if [ -f "${HOME}/.${app_name}.branch" ]; then
    branch_name=$(<"${HOME}/.${app_name}.branch")
else
    branch_name="master"
fi
# Python library of common functions to be used
commonlibbranch="v2_0"

# determine machine identity
host_name=$(hostname)

# construct database paths
database_filename="kimnaty.sqlite3"
database_path="/srv/databases"
db_full_path="${database_path}/${database_filename}"
website_dir="/tmp/${app_name}/site"
website_image_dir="${website_dir}/img"

constants_sh_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)

# list of timers provided
declare -a kimnaty_timers=("kimnaty.trend.day.timer"
        "kimnaty.trend.month.timer"
        "kimnaty.trend.year.timer"
        "kimnaty.update.timer")
# list of services provided
declare -a kimnaty_services=("kimnaty.kimnaty.service" "kimnaty.bluepy-helper-killer.service")

# Install python3 and develop packages
# Support for matplotlib & numpy needs to be installed seperately
# Support for serial port
# SQLite3 support (incl python3)
declare -a kimnaty_apt_packages=("build-essential" "python3" "python3-dev" "python3-pip"
        "libatlas-base-dev" "libxcb1" "libopenjp2-7" "libtiff5" "libglib2.0-dev"
        "pi-bluetooth" "bluetooth" "bluez"
        "sqlite3")
# placeholders for trendgraphs to make website work regardless of the state of the graphs.
declare -a kimnaty_graphs=('kim_days_compressor.png'
        'kim_days_temperature.png'
        'kim_hours_humidity.png'
        'kim_hours_voltage.png'
        'kim_months_temperature_ac.png'
        'kim_days_humidity.png'
        'kim_days_voltage.png'
        'kim_hours_temperature_ac.png'
        'kim_months_compressor.png'
        'kim_months_temperature.png'
        'kim_days_temperature_ac.png'
        'kim_hours_compressor.png'
        'kim_hours_temperature.png'
        'kim_months_humidity.png'
        'kim_months_voltage.png')

# start the application
start_kimnaty() {
    GRAPH=$2
    ROOT_DEAR=$1
    echo "Starting ${app_name} on $(date)"
    # make sure /tmp environment exists
    boot_kimnaty
    if [ "${GRAPH}" == "-graph" ]; then
        graph_kimnaty "${ROOT_DEAR}"
    fi
    action_timers start
    action_services start
    cp "${constants_sh_dir}/../www/index.html" "${website_dir}"
    cp "${constants_sh_dir}/../www/favicon.ico" "${website_dir}"
}

# stop the application
stop_kimnaty() {
    echo "Stopping ${app_name} on $(date)"
    action_timers stop
    action_services stop
}

# update the repository
update_kimnaty() {
    git fetch origin || sleep 60
    git fetch origin
    DIFFLIST=$(git --no-pager diff --name-only "${branch_name}..origin/${branch_name}")
    git pull
    git fetch origin
    git checkout "${branch_name}"
    git reset --hard "origin/${branch_name}" && git clean -f -d
}

# create graphs
graph_kimnaty() {
    ROOT_DIR=$1

    echo "Creating graphs [1]"
    . "${ROOT_DIR}/bin/pastday.sh"
    echo "Creating graphs [2]"
    . "${ROOT_DIR}/bin/pastmonth.sh"
    echo "Creating graphs [3]"
    . "${ROOT_DIR}/bin/pastyear.sh"
}

# stop, update the repo and start the application
# do some additional stuff when called by systemd
restart_kimnaty() {
    ROOT_DIR=$1

    # restarted by --systemd flag
    SYSTEMD_REQUEST=$2

    echo "Restarting ${app_name} on $(date)"
    stop_kimnaty

    update_kimnaty

    if [ "${SYSTEMD_REQUEST}" -eq 1 ]; then
        SYSTEMD_REQUEST="-graph"
    else
        echo "Skipping graph creation"
        SYSTEMD_REQUEST="-nograph"
    fi

    # re-install services and timers in case they were changed
    sudo cp "${ROOT_DIR}"/services/*.service /etc/systemd/system/
    sudo cp "${ROOT_DIR}"/services/*.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl reset-failed

    start_kimnaty "${ROOT_DIR}" "${SYSTEMD_REQUEST}"
}

# uninstall the application
unstall_kimnaty() {
    echo "Uninstalling ${app_name} on $(date)"
    stop_kimnaty
    action_timers disable
    action_services disable
    action_timers rm
    action_services rm
    rm "${HOME}/.${app_name}.branch"
}

# install the application
install_kimnaty() {
    ROOT_DIR=$1

    # to suppress git detecting changes by chmod
    git config core.fileMode false
    # note the branchname being used
    if [ ! -e "${HOME}/.${app_name}.branch" ]; then
        echo "${branch_name}" >"${HOME}/.${app_name}.branch"
    fi

    echo "Installing ${app_name} on $(date)"
    # install APT packages
    for PKG in "${kimnaty_apt_packages[@]}"; do
        action_apt_install "${PKG}"
    done

    echo "Activating BT-support..."
    sudo addgroup --gid 112 bluetooth
    sudo usermod -aG bluetooth pi
    sudo rm /etc/modprobe.d/dietpi-disable_bluetooth.conf
    sudo sed -i /^[[:blank:]]*dtoverlay=disable-bt/d /boot/config.txt
    echo

    # install Python3 stuff
    python3 -m pip install --upgrade pip setuptools wheel
    python3 -m pip install -r requirements.txt
    echo
    echo "Uninstalling common python functions..."
    python3 -m pip uninstall -y bluepy
    python3 -m pip uninstall -y mausy5043-common-python
    echo
    echo "Installing common python functions..."
    python3 -m pip install "git+https://github.com/Mausy5043/bluepy@master#egg=bluepy"
    echo
    echo -n "Installed: "
    python3 -m pip list | grep bluepy
    python3 -m pip install "git+https://github.com/Mausy5043/mausy5043-common-python.git@${commonlibbranch}#egg=mausy5043-common-python"

    if [ -f "${db_full_path}" ]; then
        echo "Found existing database."
    else
        echo "Creating database."
        sqlite3 "${db_full_path}" <"${ROOT_DIR}/bin/kimnaty.sql"
    fi

    # install services and timers
    echo "Installing timers & services."
    sudo cp "${ROOT_DIR}"/services/*.service /etc/systemd/system/
    sudo cp "${ROOT_DIR}"/services/*.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    action_timers enable
    action_services enable

    # install a link to the website on /tmp/....
    ln -s "${website_dir}" /var/www/state

    echo "Installation complete. To start the application use:"
    echo "   kimnaty --go"
}

# set-up the application
boot_kimnaty() {
    # make sure website filetree exists
    if [ ! -d "${website_image_dir}" ]; then
        mkdir -p "${website_image_dir}"
        chmod -R 755 "${website_dir}/.."
    fi
    # allow website to work even if the graphics have not yet been created
    for GRPH in "${kimnaty_graphs[@]}"; do
        create_graphic "${GRPH}"
    done
    cp "${constants_sh_dir}/../www/index.html" "${website_dir}"
    cp "${constants_sh_dir}/../www/favicon.ico" "${website_dir}"
}

# perform systemctl actions on all timers
action_timers() {
    ACTION=$1
    for TMR in "${kimnaty_timers[@]}"; do
        if [ "${ACTION}" != "rm" ]; then
            sudo systemctl "${ACTION}" "${TMR}"
        else
            sudo rm "/etc/systemd/system/${TMR}"
        fi
    done
    sudo systemctl daemon-reload
    sudo systemctl reset-failed
}

# perform systemctl actions on all services
action_services() {
    ACTION=$1
    for SRVC in "${kimnaty_services[@]}"; do
        if [ "${ACTION}" != "rm" ]; then
            sudo systemctl "${ACTION}" "${SRVC}"
        else
            sudo rm "/etc/systemd/system/${SRVC}"
        fi
    done
    sudo systemctl daemon-reload
    sudo systemctl reset-failed
}

# See if packages are installed and install them using apt-get
action_apt_install() {
    PKG=$1
    echo "*********************************************************"
    echo "* Requesting ${PKG}"
    status=$(dpkg -l | awk '{print $2}' | grep -c -e "^${PKG}*")
    if [ "${status}" -eq 0 ]; then
        echo -n "* Installing ${PKG} "
        sudo apt-get -yqq install "${PKG}" && echo " ... [OK]"
        echo "*********************************************************"
    else
        echo "* Already installed !!!"
        echo "*********************************************************"
    fi
    echo
}

# copy files from the network to the local .config folder
getfilefromserver() {
    file="${1}"
    mode="${2}"

    cp -rvf "/srv/config/${file}" "${HOME}/.config/"
    chmod -R "${mode}" "${HOME}/.config/${file}"
}

# create a placeholder graphic for Fles if it doesn't exist already
create_graphic() {
    IMAGE="$1"
    if [ ! -f "${IMAGE}" ]; then
        cp "${constants_sh_dir}/../www/empty.png" "${IMAGE}"
    fi
}

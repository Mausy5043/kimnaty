#!/bin/bash

# query daily totals for a period of one month

MAINTENANCE=${1}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)

pushd "${HERE}" >/dev/null || exit 1
# shellcheck disable=SC1091
source include.sh

if [ "${MAINTENANCE}" == "-" ]; then
    # do some maintenance
    CURRENT_EPOCH=$(date +'%s')

    # shellcheck disable=SC2154
    echo "${db_full_path} re-indexing... "
    sqlite3 "${db_full_path}" "REINDEX;"

    echo -n "${db_full_path} integrity check:   "
    chk_result=$(sqlite3 "${db_full_path}" "PRAGMA integrity_check;")
    echo " ${chk_result}"
    if [ "${chk_result}" == "ok" ]; then
        echo "${db_full_path} copying to backup... "
        # copy to backup
        if command -v rclone &> /dev/null; then
            # shellcheck disable=SC2154
            rclone copyto -v \
                   "${database_local_root}/${app_name}/${database_filename}" \
                   "${database_remote_root}/backup/${database_filename}"
        fi

        # Keep upto 10 years of data
        echo "${db_full_path} vacuuming... "
        PURGE_EPOCH=$(echo "${CURRENT_EPOCH} - (3660 * 24 * 3600)" |bc)
        sqlite3 "${db_full_path}" \
                "DELETE FROM data WHERE sample_epoch < ${PURGE_EPOCH};"
        sqlite3 "${db_full_path}" \
                "DELETE FROM aircon WHERE sample_epoch < ${PURGE_EPOCH};"
    fi
    # sync the database into the cloud
    if command -v rclone &> /dev/null; then
        echo "${db_full_path} syncing... "
        # shellcheck disable=SC2154
        rclone copyto -v \
               "${database_local_root}/${app_name}/${database_filename}" \
               "${database_remote_root}/${app_name}/${database_filename}"
    fi
fi

./trend.py --days 0

popd >/dev/null || exit

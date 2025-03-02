
[![License](https://img.shields.io/github/license/mausy5043/kimnaty)](LICENSE)
![Static Badge](https://img.shields.io/badge/release-rolling-lightgreen)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-008800.svg)](https://github.com/astral-sh/ruff)
[![Linter: ruff](https://img.shields.io/badge/linter-ruff-008800.svg)](https://github.com/astral-sh/ruff)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Mausy5043/kimnaty/master.svg)](https://results.pre-commit.ci/latest/github/Mausy5043/kimnaty/master)
[![Dependabot Updates](https://github.com/Mausy5043/kimnaty/actions/workflows/dependabot/dependabot-updates/badge.svg)](https://github.com/Mausy5043/kimnaty/actions/workflows/dependabot/dependabot-updates)

# kimnaty (кімнати)

## introduction

Monitoring LYWSD03MMC devices in various rooms in my house. Storing room temperature and humidity as well as the
device's battery level.

It has been observed that these devices sometime fail to connect even when the battery level is still sufficient.
Therefore the app also tries to assess the state of the device based on Bluetooth information (notably connection
failures). All collected data is stored locally.

## (un)installing

Designed and tested to work on Raspberry Pi (DietPi).
To install run: `kimnaty --install`.
Use `kimnaty --uninstall` to uninstall.

## requirements
The app uses [`rclone`](https://rclone.org/) to upload the local database to a private dropbox account for
disaster recovery purposes.
The app uses [`pylywsdxx`](https://pypi.org/project/pylywsdxx/) which in turn
needs [`bluepy3`](https://pypi.org/project/bluepy3/). Both are automagically installed during the installation
of the app together with any Bluetooth support needed.

## user defaults
User can set defaults for trending graphs in `~.local/kimnaty.json` as follows:
```(json)
{
  "trend": {"hours": 25,
            "months": 25,
            "days": 14}
}
```
All entries are case-sensitive(!) and optional. The application will use default values for options that are not present.

## acknowledgements
### libdaikin

Code for reading the state of compatible Daikin airconditioners stolen in 2021
from: https://github.com/arska/python-daikinapi

## Disclaimer & License
As of September 2024 `pylywsdxx` is distributed under [AGPL-3.0-or-later](LICENSE).

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


## acknowledgements
### libdaikin

Code for reading the state of compatible Daikin airconditioners stolen in 2021
from: https://github.com/arska/python-daikinapi

## the name

kimnaty (or кімнати) is Ukranian for "rooms". Given the current state of the world (MAR2022) I thought a Ukranian name
for this repo to be a fitting tribute to the heroic people of Ukraine.   
слава україні !

# wiffi2openhab

wiffi2openhab is a python script that runs as a service. It collects data from "wiffi" devices, see stall.biz for details. The devices (including Weatherman, Rainyman, ...) send their data JSON formatted to a TCP socket. The script opens a TCP socket, collects the sent messages and forwards the configured items to an openHAB instance using the openHAB REST API.

The script supports multiple devices at the same time (= one instance of the script running as a service handles multiple wiffi devices). The openhab item names doesn't have to match the wiffi names, because the scripts allows to translate the names.

The configuration is part of the script, the script has to be edited to configure:
- TCP server port
- openHAB address
- wiffi device address and supported reading

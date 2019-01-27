#!/usr/bin/python3
import json
import socketserver
from openhab import OpenHAB

class MyTCPHandler(socketserver.StreamRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """
    def handle(self):
        # self.request is the TCP socket connected to the client
        self.server.wiffi_mgr.process(self.client_address[0], self.rfile.readline().strip())


class WiffiItem:
    def __init__(self, homematic_name, target_name):
        self.homematic_name = homematic_name
        self.target_name = target_name

    def convert_value(self, value):
        return value


class WiffiItemSwitch(WiffiItem):
    def __init__(self, homematic_name, target_name):
        WiffiItem.__init__(self, homematic_name, target_name)

    def convert_value(self, value):
        return 'ON' if value else 'OFF'


class Wiffi:
    """ represents a single wiffi device """
    def __init__(self, client_address, modultyp, item_map):
        self.client_address = client_address
        self.modultyp = modultyp
        self.buffer = b''       # ring buffer for received raw string data
        self.items = {}     # dict of items, key is homematic_name string

        # create dict for faster access
        for item in item_map:
            self.items[item.homematic_name] = item

    def process(self, data, target):
        # add data from stream to ring buffer
        self.buffer = self.buffer + data
        pos = self.buffer.find(b'\x04')
        while pos >= 0:
            self.parse_msg(self.buffer[:pos], target)
            self.buffer = self.buffer[pos + 1:]
            pos = self.buffer.find(b'\x04')

    def parse_msg(self, raw_data, target):
        try:
            data = json.loads(raw_data.decode('utf-8'))
            if data['modultyp'] != self.modultyp:
                print("incompatible module-type configured:{c:s}, received:{r:s}".format(c=self.modultyp, r=data['modultyp']))
                return

            for var in data['vars']:
                if var['homematic_name'] in self.items:
                    item = self.items[var['homematic_name']]
                    target.set_state(item.target_name, item.convert_value(var['value']))
                elif var['name'] in self.items:
                    item = self.items[var['name']]
                    target.set_state(item.target_name, item.convert_value(var['value']))
        except Exception as e:
            print('EXCEPTION {}\n{}', repr(e), raw_data)


class WiffiManager:
    """ manages a list of wiffi's, unique item is the ip address """
    def __init__(self, target):
        self.wiffis = {}    # dict of registered wiffis, key = ip address string
        self.target = target

    def add(self, wiffi):
        self.wiffis[wiffi.client_address] = wiffi

    def process(self, ip, data):
        #print('RX {}: {}'.format(ip, data))
        if ip not in self.wiffis:
            print("wiffi with ip {ip:s} not found".format(ip=ip))
            return

        self.wiffis[ip].process(data, self.target)


class MyOpenHAB(OpenHAB):
    def __init__(self, ip):
        OpenHAB.__init__(self, 'http://{}/rest'.format(ip))

    def set_state(self, name, state):
        item = self.get_item(name)
        item.state = state


if __name__ == "__main__":
    HOST, PORT = '', 8189
    OPENHAB_URL = '192.168.0.22:8080'

    print("looking for openhab at {}".format(OPENHAB_URL))
    # create openhab instance
    oh = MyOpenHAB(OPENHAB_URL)

    # create wiffi instances
    mgr = WiffiManager(oh)
    mgr.add(Wiffi('192.168.0.40', 'weatherman', [
        WiffiItem('w_temperature', 'TempAussen'),
        WiffiItem('29', 'TempAussenAvgYesterday'),
        WiffiItem('w_humidity', 'HumiAussen'),
        WiffiItem('w_barometer', 'PressAussen'),
        WiffiItem('w_lux', 'IlluAussen'),
        WiffiItem('w_sonne_heute', 'SunshineHoursToday'),
        WiffiItem('w_sonne_gestern', 'SunshineHoursYesterday'),
        WiffiItemSwitch('w_sonne_scheint', 'SunIsShining'),
        WiffiItem('w_rain_intensity', 'RainAmount'),
        WiffiItem('w_rain_volume_1', 'RainAmountLast1Hour'),
        WiffiItem('w_rain_volume_24', 'RainAmountLast24Hours'),
        WiffiItem('w_rain_yesterday', 'RainAmountYesterday'),
        WiffiItemSwitch('w_rain_status', 'IsRaining'),
        WiffiItem('w_wind_avg', 'WindSpeedAvg'),
        WiffiItem('w_wind_peak', 'WindSpeedPeak'),
        WiffiItem('w_wind_dir', 'WindDirectionDeg'),
        WiffiItem('w_wind_direction', 'WindDirectionStr'),
    ]))

    # Create the server
    try:
        server = socketserver.TCPServer((HOST, PORT), MyTCPHandler)
        print("listening for wiffis on port", PORT)
        server.wiffi_mgr = mgr
        server.serve_forever()
    finally:
        server.server_close()

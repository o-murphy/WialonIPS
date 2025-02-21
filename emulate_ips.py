import random
import socket
import time
from datetime import datetime

import geocoder

from wialonips.crc16 import crc16
from wialonips.protocol import PacketType, Protocol

# HOST = "127.0.0.1"
# PORT = 65432

HOST = "193.193.165.165"
PORT = 20332
# PORT = 20963

IMEI = "wips"
PASSWORD = "wips"

INCOMING_PACKET_FORMAT = "#{type}#{params}{crc}\r\n"

login_body = ";".join(["2.0", IMEI, PASSWORD, ""]).encode('ascii')
print(login_body)

login_packet = {
    'type': PacketType.DEV_LOGIN.value,
    'params': login_body.decode('ascii'),
    'crc': f"{crc16(login_body):0X}"
}
# ('L', '2.0;wips;wips', '2.0;wips;wips', None)
# ('L', '2.0;wips;wips;', '2.0;wips;wips', '1C7C')

login_packet = INCOMING_PACKET_FORMAT.format(**login_packet).encode('ascii')
print(login_packet)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
    client_socket.connect((HOST, PORT))  # Connect to server

    client_socket.send(
        login_packet
    )  # Send data
    print(">>>", login_packet)
    data = client_socket.recv(1024)  # Receive response
    print("<<<", data)

    if data == b'#AL#1\r\n':
        while True:
            g = geocoder.ip('me')
            lat, lon = g.latlng
            dt = datetime.now()
            # data_body = Protocol().build_short_data_packet(dt, lat, lon, 0, 0, 100, 7)
            data_body = Protocol().build_data_packet(
                date_time=dt,
                lat=lat,
                lon=lon,
                speed=random.randint(0, 140),
                course=random.randint(0, 359),
                alt=100,
                sats=random.randint(7, 20),
                alarm=False,
                hdop=random.randint(1, 10),
                adc=[random.random(), random.random()],
                param1=random.randint(1, 10),
                param2=random.randint(1, 10),
                param3=random.randrange(1, 10),
                # text="Message from driver",
                text1="sample text",
                ibutton="wipsdriver",
                inputs=0b_0000_0000_0000_0000_0000_0100_0000_0010,
                outputs=0b_0000_0000_0000_0000_0000_0100_0001_0000,
                mmc1="255",
                mnc1="01",
                lac0="0",
                cell_id0="0",
                battery=70,
            )
            client_socket.send(data_body)
            print(">>>", data_body)
            data = client_socket.recv(1024)
            print("<<<", data)
            time.sleep(20)

print(f"Received from server: {data.decode()}")

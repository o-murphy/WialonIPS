import socket
import time
from datetime import datetime

import geocoder

from wialonips.protocol import PacketType, DevPacket, Protocol

HOST = "193.193.165.165"
PORT = 20332

# HOST = "127.0.0.1"
# PORT = 65432

IMEI = "wips"
PASSWORD = "wips"

INCOMING_PACKET_FORMAT = "#{type}#{params};{crc}\r\n"

login_body = ";".join(["2.0", IMEI, PASSWORD]).encode('ascii')

login_packet = {
    'type': PacketType.DEV_LOGIN.value,
    'params': login_body.decode('ascii'),
    'crc': DevPacket.crc_body(login_body).decode('ascii')
}

login_packet = INCOMING_PACKET_FORMAT.format(**login_packet).encode('ascii')
print(login_packet)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
    client_socket.connect((HOST, PORT))  # Connect to server

    client_socket.send(
        login_packet
    )  # Send data
    print("Sent")
    data = client_socket.recv(1024)  # Receive response
    print("Received", data)
    if data == b'#AL#1\r\n':
        while True:
            g = geocoder.ip('me')
            lat, lon = g.latlng
            dt = datetime.now()
            data_body = Protocol().build_short_data_packet(dt, lat, lon, 0, 0, 100, 7)

            client_socket.send(data_body)
            data = client_socket.recv(1024)
            time.sleep(3)

print(f"Received from server: {data.decode()}")

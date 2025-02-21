import socket
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict

from wialonips.protocol import Protocol, PacketType, DevPacket


@dataclass
class DeviceCredentials:
    IMEI: str
    PASSWORD: Optional[str] = None
    PROTOCOL_VERSION: str = "2.0"


@dataclass
class Device:
    connection: socket.socket
    credentials: DeviceCredentials
    protocol: Optional[Protocol] = field(init=False, default=None)

    def __post_init__(self):
        self.protocol = Protocol()

    def on_message_received(self, packet: DevPacket):

        if packet.type == PacketType.DEV_LOGIN:
            self.on_login(packet)
        elif packet.type == PacketType.DEV_EXTENDED_DATA:
            self.on_extended(packet)
        elif packet.type == PacketType.DEV_SHORT_DATA:
            self.on_short(packet)
        elif packet.type == PacketType.DEV_PING:
            self.on_ping(packet)

    def on_login(self, packet):
        raise NotImplementedError

    def on_short(self, packet: DevPacket):
        self.connection.send(b'#AD#1\r\n')

    def on_extended(self, packet: DevPacket):
        self.connection.send(b'#AD#1\r\n')

    def on_ping(self, packet: DevPacket):
        self.connection.send(b'#AP#\r\n')

    # def query_stream(self):
    #     raise NotImplementedError
    #
    # def stop_stream(self):
    #     raise NotImplementedError
    #
    # def on_stream_block(self):
    #     raise NotImplementedError
    #
    # def query_video(self):
    #     raise NotImplementedError
    #
    # def stop_video(self):
    #     raise NotImplementedError
    #
    # def on_video_block(self):
    #     raise NotImplementedError
    #
    # def query_video_list(self):
    #     raise NotImplementedError
    #
    # def upload_software(self):
    #     raise NotImplementedError
    #
    # def upload_configuration(self):
    #     raise NotImplementedError
    #
    # def driver_message(self):
    #     raise NotImplementedError
    #
    # def on_driver_message(self):
    #     raise NotImplementedError
    #
    # def query_image(self):
    #     raise NotImplementedError
    #
    # def on_image(self):
    #     raise NotImplementedError
    #
    # def query_ddd_info(self):
    #     raise NotImplementedError
    #
    # def on_ddd_info(self):
    #     raise NotImplementedError
    #
    # def on_ddd_block(self):
    #     raise NotImplementedError
    #
    # def custom(self):
    #     raise NotImplementedError


class Server:

    def __init__(self, host: str = "127.0.0.1", port: int = 65432):
        self.host = host
        self.port = port
        self.devices: Dict[str, DeviceCredentials] = {}
        self.socket = None
        self.protocol = Protocol()
        self.active_imeis: set = set()  # Track active IMEIs

    def handle_connection(self, conn, addr):
        """Handles communication with a single device (client)."""
        print(f"Connected by {addr}")
        device_imei = None
        dev = None

        try:
            while True:
                data = conn.recv(1024)  # Receive data (1024 bytes max)
                if not data:
                    print(f"Connection closed by {addr}")
                    break

                print(f"Received from {addr}: {data.decode()}")

                message = self.protocol.parse_incoming_packet(data)
                print(message)

                # Handle DEV_LOGIN only once, then bind the device
                if message.type == PacketType.DEV_LOGIN:
                    if message.imei in self.active_imeis:
                        print(f"Device {message.imei} already connected, rejecting login")
                        conn.send(b"#AL#0\r\n")  # Reject the connection
                        break  # Close the connection if IMEI is already active

                    if message.imei not in self.devices:
                        print(f"Device {message.imei} not registered")
                        conn.send(b"#AL#01\r\n")  # Reject the connection
                        break  # Close the connection if IMEI is already active
                    if self.devices[message.imei].PASSWORD != message.password:
                        print(f"Wrong password for device {message.imei}")
                        conn.send(b"#AL#01\r\n")
                        break

                    conn.send(b"#AL#1\r\n")

                    # Bind the connection to the device
                    device_imei = message.imei
                    self.active_imeis.add(device_imei)  # Mark this IMEI as active
                    dev = Device(conn, self.devices[message.imei])

                    print(f"Device {device_imei} authenticated")

                # Now handle all subsequent messages for this device (no more DEV_LOGIN)
                elif device_imei and dev and self.devices.get(device_imei):
                    print(f"Processing message for device {device_imei}")
                    # Handle any message that is not a DEV_LOGIN
                    dev.on_message_received(message)

                else:
                    print(f"Device not authenticated yet, ignoring message from {addr}")
                    # continue
                    break

        finally:
            if device_imei:
                print(f"Closing connection for device {device_imei}")
                self.active_imeis.remove(device_imei)  # Remove the IMEI from active connections
            conn.close()

    def run(self):
        """Runs the server to accept multiple client connections."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.socket:
            self.socket.bind((self.host, self.port))
            self.socket.listen()
            print(f"Server listening on {self.host}:{self.port}")

            while True:
                conn, addr = self.socket.accept()  # Accept a new connection
                client_thread = threading.Thread(target=self.handle_connection, args=(conn, addr))
                client_thread.daemon = True  # Allow thread to be killed when the program exits
                client_thread.start()

    def register_device(self, device: DeviceCredentials):
        if not device.IMEI in self.devices:
            self.devices[device.IMEI] = device
            return

        raise Exception(f"Device {device.IMEI} already exists")

    def unregister_device(self, device: DeviceCredentials):
        if not device.IMEI in self.devices:
            raise Exception(f"Device {device.IMEI} not registered")
        self.devices.pop(device.IMEI)

    def on_message_received(self, msg: bytes):
        raise NotImplementedError


if __name__ == "__main__":
    server = Server()
    dev1 = DeviceCredentials("65432", "65432")
    dev2 = DeviceCredentials("111111", "222222")
    server.register_device(dev1)
    server.register_device(dev2)
    server.run()

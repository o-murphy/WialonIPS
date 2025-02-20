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
    # server: Optional['Server'] = None
    credentials: DeviceCredentials
    # credentials: Optional[DeviceCredentials] = field(init=False, default=None)
    protocol: Optional[Protocol] = field(init=False, default=None)

    def __post_init__(self):
        self.protocol = Protocol()

    def on_message_received(self, packet: DevPacket):

        # def on_message_received(self, message: bytes):
        #     packet = self.protocol.parse_incoming_packet(message)
        #     print(packet)

        if packet.Type == PacketType.DEV_LOGIN:
            self.on_login(packet)
        elif packet.Type == PacketType.DEV_EXTENDED_DATA:
            self.on_extended(packet)
        elif packet.Type == PacketType.DEV_SHORT_DATA:
            self.on_short(packet)

    def on_login(self, packet):
        raise NotImplementedError

    #
    # def on_login(self, packet):
    #
    #     if packet.imei in self.server.active_imeis:
    #         self.connection.send(b"#AL#0\r\n")  # Reject the connection
    #         raise PermissionError(f"Device {packet.imei} already connected, rejecting login")
    #     if packet.imei not in self.server.devices:
    #         self.connection.send(b"#AL#01\r\n")  # Reject the connection
    #         raise PermissionError(f"Device {packet.imei} not registered")
    #     if self.server.devices[packet.imei].PASSWORD != packet.password:
    #         self.connection.send(b"#AL#01\r\n")
    #         raise PermissionError(f"Wrong password for device {packet.imei}")
    #
    #     self.connection.send(b"#AL#1\r\n")
    #     self.credentials = DeviceCredentials(packet.imei, packet.password)
    #
    #     print(f"Device {packet.imei} authenticated")

    def on_short(self, packet: DevPacket):
        self.connection.send(b'#AD#1\r\n')

    def on_extended(self, packet: DevPacket):
        self.connection.send(b'#AD#1\r\n')

    @classmethod
    def on_ping(cls):
        raise NotImplementedError

    @classmethod
    def query_stream(cls):
        raise NotImplementedError

    @classmethod
    def stop_stream(cls):
        raise NotImplementedError

    @classmethod
    def on_stream_block(cls):
        raise NotImplementedError

    @classmethod
    def query_video(cls):
        raise NotImplementedError

    @classmethod
    def stop_video(cls):
        raise NotImplementedError

    @classmethod
    def on_video_block(cls):
        raise NotImplementedError

    @classmethod
    def query_video_list(cls):
        raise NotImplementedError

    @classmethod
    def upload_software(cls):
        raise NotImplementedError

    @classmethod
    def upload_configuration(cls):
        raise NotImplementedError

    @classmethod
    def driver_message(cls):
        raise NotImplementedError

    @classmethod
    def on_driver_message(cls):
        raise NotImplementedError

    @classmethod
    def query_image(cls):
        raise NotImplementedError

    @classmethod
    def on_image(cls):
        raise NotImplementedError

    @classmethod
    def query_ddd_info(cls):
        raise NotImplementedError

    @classmethod
    def on_ddd_info(cls):
        raise NotImplementedError

    @classmethod
    def on_ddd_block(cls):
        raise NotImplementedError

    @classmethod
    def custom(cls):
        raise NotImplementedError


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
        # dev = Device(conn, server)

        try:
            while True:
                data = conn.recv(1024)  # Receive data (1024 bytes max)
                if not data:
                    print(f"Connection closed by {addr}")
                    break

                print(f"Received from {addr}: {data.decode()}")

                # dev.on_message_received(data)

                message = self.protocol.parse_incoming_packet(data)
                print(message)

                # Handle DEV_LOGIN only once, then bind the device
                if message.Type == PacketType.DEV_LOGIN:
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
                    # For example, you can check for other packet types and handle them here
                    # if r.Type == PacketType.SOME_OTHER_TYPE:
                    #     pass
                    dev.on_message_received(message)


                else:
                    print(f"Device not authenticated yet, ignoring message from {addr}")
                    # continue
                    break

                # conn.sendall(data)  # Echo data back to client

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
    # if r.imei != "65432" or r.password != "65432":
    #     conn.send(b"#AL#0\r\n")

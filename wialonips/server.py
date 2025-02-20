from dataclasses import dataclass, field
from typing import Optional, Dict


@dataclass
class Device:
    IMEI: str
    PASSWORD: Optional[str] = None
    PROTOCOL_VERSION: str = "2.0"
    _server: Optional['Server'] = field(init=False)

    def __post_init__(self):
        ...

    def bind_server(self, server):
        self._server = server

    def unbind_server(self):
        self._server = None

    @classmethod
    def on_login(self):
        raise NotImplementedError

    @classmethod
    def on_short(cls):
        raise NotImplementedError

    @classmethod
    def on_extended(cls):
        raise NotImplementedError

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

    def __init__(self):
        self.devices: Dict[str, Device] = {}

    def register_device(self, device: Device):
        if not device.IMEI in self.devices:
            device.bind_server(self)
            self.devices[device.IMEI] = device
            return

        raise Exception(f"Device {device.IMEI} already exists")

    def unregister_device(self, device: Device):
        if not device.IMEI in self.devices:
            raise Exception(f"Device {device.IMEI} not registered")
        self.devices.pop(device.IMEI)

    def on_message_received(self, msg: bytes):
        raise NotImplementedError

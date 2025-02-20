from dataclasses import dataclass
from typing import Optional


@dataclass
class Device:
    IMEI: str
    PASSWORD: Optional[str] = None
    PROTOCOL_VERSION: str = "2.0"

    def __post_init__(self):
        ...

    @classmethod
    def login(self):
        ...

    @classmethod
    def short(cls):
        ...

    @classmethod
    def extended(cls):
        ...

    @classmethod
    def ping(cls):
        ...

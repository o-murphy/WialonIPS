import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Any


class PacketType(str, Enum):
    DEV_LOGIN = "L"
    SRV_LOGIN_RESPONSE = "AL"
    DEV_SHORT_DATA = "SD"
    SRV_SHORT_DATA_RESPONSE = "ASD"
    DEV_EXTENDED_DATA = "D"
    SRV_EXTENDED_DATA_RESPONSE = "AD"
    DEV_BLACKBOX = "B"
    SRV_BLACKBOX_RESPONSE = "AB"

    SRV_VIDEO_STREAM_QUERY = "QLV"
    DEV_VIDEO_STREAM = "LV"

    SRV_VIDEO_RECORD_QUERY = "QPB"
    DEV_VIDEO_RECORD = "PB"

    SRV_VIDEO_STREAM_STOP_QUERY = "QVS"
    DEV_VIDEO_STREAM_STOP = "VS"

    SRV_VIDEO_FILE_QUERY = "QVF"
    DEV_VIDEO_FILE = "VF"

    SRV_VIDEO_FILE_LIST_QUERY = "QTM"
    DEV_VIDEO_FILE_LIST_RESPONSE = "TM"

    DEV_PING = "P"
    SRV_PING = "AP"

    SRV_UPLOAD_SOFTWARE = "US"
    SRV_UPLOAD_CONFIGURATION = "UC"

    DRV_MESSAGE = "M"
    SRV_DRV_MESSAGE_RESPONSE = "AM"

    SRV_IMAGE_QUERY = "QI"
    DEV_IMAGE = "I"
    SRV_IMAGE_RESPONSE = "AI"

    SRV_DDD_QUERY = "QT"
    DEV_DDD_INFO = "IT"

    SRV_DDD_INFO_RESPONSE = "AIT"
    DEV_DDD = "T"
    SRV_DDD_RESPONSE = "AT"


class LoginResponseCode(str, Enum):
    OK = "1"
    ERROR = "0"
    AUTH_ERROR = "01"
    CRC_ERROR = "10"

class ExtendedDataResponseCode(str, Enum):
    STRUCT_ERROR = "-1"
    INVALID_TIMESTAMP = "0"
    OK = "1"
    COORDINATE_ERROR = "10"
    MOVE_PROPS_ERROR = "11"
    SATS_ERROR = "12"
    IO_PROPS_ERROR = "13"
    ADC_PROPS_ERROR = "14"
    PARAMS_ERROR = "15"
    PARAM_NAME_LEN_ERROR = "15.1"
    PARAM_NAME_ERROR = "15.2"
    CRC_ERROR = "16"


class ShortDataResponseCode(str, Enum):
    STRUCT_ERROR = "-1"
    INVALID_TIMESTAMP = "0"
    OK = "1"
    COORDINATE_ERROR = "10"
    MOVE_PROPS_ERROR = "11"
    SATS_ERROR = "12"
    CRC_ERROR = "13"


SEPARATOR = ";"
NOT_AVAILABLE = "NA"
ALARM_PARAM = "SOS"
LBS_MMC_PARAM = "mcc%d"
LBS_MNC_PARAM = "mnc%d"
LBS_LAC_PARAM = "lac%d"
LBS_CELL_ID_PARAM = "cell_id%d"
WIFI_MAC_PARAM = "wifi_mac_%d"
WIFI_RSSI_PARAM = "wifi_rssi_%d"


@dataclass
class Packet:
    Type: Optional[PacketType] = None
    Code: Optional[Any] = None
    Body: Optional[Any] = None
    RAW: Optional[bytes] = None


def _stringify(object):
    if object is None:
        return NOT_AVAILABLE
    if hasattr(object, "__str__"):
        return str(object)


class Protocol:

    def __init__(self, version="2.0"):
        self.version = version

    def build_login_packet(self, imei, password):
        return self.build_packet(PacketType.DEV_LOGIN, data=[imei, password])

    def build_data_packet(self,
                          date_time: Optional[datetime] = None,
                          lat_deg: Optional[float] = None,
                          lat_sign=None,
                          lon_deg: Optional[float] = None,
                          lon_sing=None,
                          speed: Optional[int] = None,
                          course: Optional[int] = None,
                          alt: Optional[int] = None,
                          sats: Optional[int] = None,
                          hdop: Optional[float] = 1.0,
                          inputs: Optional[int] = None,
                          outputs: Optional[int] = None,
                          adc: Optional[list[float]] = "",
                          ibutton: Optional[str] = None,
                          alarm: bool = False,
                          **params,
                          ):

        if date_time is not None:
            date = date_time.strftime("%d%m%y")
            time = f'{date_time.strftime("%H%M%S")}.{date_time.microsecond * 1000:09d}'
        else:
            date, time = None, None

        if not (0 <= course < 360):
            raise ValueError("Course must be between 0 and 360")

        if speed is not None and speed < 0:
            raise ValueError("Speed must be positive")

        if sats is not None and sats < 0:
            raise ValueError("Sats must be positive")

        if adc:
            adc = ",".join([_stringify(i) for i in adc])

        if alarm:
            params[ALARM_PARAM] = 1

        params = ','.join([f"{_stringify(k)}:{_stringify(v)}" for k, v in params.items()])

        data = [_stringify(i) for i in (
            date, time, lat_deg, lat_sign, lon_deg, lon_sing,
            speed, course, alt, sats,
            hdop, inputs, outputs, adc, ibutton,
            params
        )]

        return self.build_packet(PacketType.DEV_EXTENDED_DATA, data=data)

    def build_short_data_packet(self,
                                date_time: Optional[datetime] = None,
                                lat_deg: Optional[float] = None,
                                lat_sign=None,
                                lon_deg: Optional[float] = None,
                                lon_sing=None,
                                speed: Optional[int] = None,
                                course: Optional[int] = None,
                                alt: Optional[int] = None,
                                sats: Optional[int] = None):

        if date_time is not None:
            date = date_time.strftime("%d%m%y")
            time = f'{date_time.strftime("%H%M%S")}.{date_time.microsecond * 1000:09d}'
        else:
            date, time = None, None

        if not (0 <= course < 360):
            raise ValueError("Course must be between 0 and 360")

        if speed is not None and speed < 0:
            raise ValueError("Speed must be positive")

        if sats is not None and sats < 0:
            raise ValueError("Sats must be positive")
        else:
            sats = NOT_AVAILABLE

        data = [_stringify(i) for i in (date, time, lat_deg, lat_sign, lon_deg, lon_sing,
                                        speed, course, alt, sats)]
        return self.build_packet(PacketType.DEV_SHORT_DATA, data=data)

    def build_black_box_packet(self, packets):
        data = "|".join(packets)
        return self.build_packet(PacketType.DEV_BLACKBOX, data=[data])

    def build_packet(self, packet_type: PacketType, data=None) -> bytes:
        header = f"#{packet_type}#{self.version}"
        if data:
            data = SEPARATOR.join([header, *data])
            packet = SEPARATOR.join([header, data]).encode("ascii")
        else:
            packet = header.encode("ascii")

        crc = b""  # TODO:
        return packet + crc + b"\r\n"

    def parse_packet(self, packet: bytes) -> Optional[Packet]:
        try:
            _packet = packet.decode('ascii')
        except UnicodeDecodeError:
            return Packet(None, LoginResponseCode.ERROR, None, packet)

        match = re.match("#(\w+)#(\d+(.\d)?)?", _packet, re.IGNORECASE)
        if not match:
            return Packet(None, LoginResponseCode.ERROR, _packet, packet)

        typ, code, subcode, *other = match.groups()
        print(typ, code, subcode, *other)

        try:
            _typ = PacketType(typ)
        except KeyError:
            return Packet(None, None, _packet, packet)

        if _typ == PacketType.SRV_EXTENDED_DATA_RESPONSE:
            code = ExtendedDataResponseCode(code)

        elif _typ == PacketType.SRV_SHORT_DATA_RESPONSE:
            code = ShortDataResponseCode(code)

        elif _typ == PacketType.SRV_LOGIN_RESPONSE:
            code = LoginResponseCode(code)

        elif _typ == PacketType.SRV_BLACKBOX_RESPONSE:
            code = code

        return Packet(_typ, code, _packet, packet)


p = Protocol()
r = p.parse_packet(b"#AD#15.1\r\n")
print(r)
r = p.parse_packet(b"#AL#1\r\n")
print(r)
r = p.parse_packet(b'#AB#\r\n')
print(r)

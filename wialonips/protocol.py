import re
from dataclasses import dataclass, fields
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Literal, Union, NamedTuple, get_type_hints


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

ParamValueTypes = {
    1: int,
    2: float,
    3: str,
}


def parse_datetime(date_str: str, time_str: str) -> datetime:
    """Convert YYMMDD and HHMMSS into a datetime object."""
    return datetime.strptime(date_str + time_str, "%y%m%d%H%M%S")


def dms_to_decimal(deg_min: str, sign: Union[Literal['N', 'S'], Literal['E', 'W']]) -> float:
    """Convert a coordinate in DDMM.MMMM format to decimal degrees."""
    if len(deg_min) < 6:
        raise ValueError("Invalid coordinate format")

    # Determine number of degrees (2 digits for latitude, 3 for longitude)
    deg_length = 2 if sign in "NS" else 3

    # Split degrees and minutes
    degrees = int(deg_min[:deg_length])
    minutes = float(deg_min[deg_length:])

    # Convert to decimal degrees
    decimal = degrees + (minutes / 60)

    # Apply sign for South/West
    if sign in "SW":
        decimal = -decimal

    return decimal


class Position(NamedTuple):
    latitude: float
    longitude: float

@dataclass
class DevPacket:
    Type: Optional[PacketType] = None
    Code: Optional[Any] = None
    RAW: Optional[bytes] = None

    imei: Optional[str] = None
    password: Optional[str] = None

    date: Optional[int] = None
    time: Optional[int] = None
    lat_deg: Optional[float] = None
    lat_sign: Optional[Literal['N', 'S']] = None
    lon_deg: Optional[float] = None  # GGGMM.MM
    lon_sign: Optional[Literal['E', 'W']] = None
    speed: Optional[int] = None
    course: Optional[int] = None
    alt: Optional[int] = None
    sats: Optional[int] = None

    hdop: Optional[float] = 1.0
    inputs: Optional[int] = None
    outputs: Optional[int] = None
    adc: Optional[list[float]] = ""
    ibutton: Optional[str] = None
    alarm: bool = False

    params: Optional[dict[str, str]] = None

    def __post_init__(self):
        self._parse_params()
        self._parse_adc()

    def _parse_adc(self):
        if self.adc and isinstance(self.adc, str):
            self.adc = [float(adc) for adc in self.adc.split(",")]

    def _parse_params(self) -> None:
        if self.params and isinstance(self.params, str):
            params = self.params.split(",")
            _params = {}

            for param in params:
                key, typ, value = param.split(":")

                if typ.isdigit() and (_typ := ParamValueTypes.get(int(typ))):
                    try:
                        _params[key] = None if value == NOT_AVAILABLE else _typ(value)
                    except TypeError:
                        _params[key] = value

            if ALARM_PARAM in _params:
                self.alarm = True
                _params.pop(ALARM_PARAM)

            self.params = _params

        else:
            self.params = None

    @property
    def datetime(self):
        if self.date and self.time:
            return parse_datetime(str(self.date), str(self.time))
        raise ValueError("Unable to parse date and time")

    @property
    def pos(self):
        if self.lat_deg and self.lat_sign and self.lon_deg and self.lon_sign:
            return Position(
                dms_to_decimal(str(self.lat_deg), self.lat_sign),
                dms_to_decimal(str(self.lon_deg), self.lon_sign),
            )







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
                          lat_deg: Optional[float] = None,  # GGMM.MM
                          lat_sign=Optional[Literal['N', 'S']],
                          lon_deg: Optional[float] = None,  # GGGMM.MM
                          lon_sing=Optional[Literal['E', 'W']],
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

    def parse_incoming_packet(self, packet: bytes) -> Optional[DevPacket]:
        try:
            _packet = packet.decode('ascii')
        except UnicodeDecodeError:
            return DevPacket(None, LoginResponseCode.ERROR, packet)

        match = re.match(r"#(\w+)#(.*)\r\n", _packet, re.IGNORECASE)
        if not match:
            print("Couldn't parse incoming packet")
            return DevPacket(None, LoginResponseCode.ERROR, packet)

        typ, params, *other = match.groups()
        _params: list[str] = [None if value == NOT_AVAILABLE else value for value in params.split(";")]

        try:
            _typ = PacketType(typ)
        except KeyError:
            return DevPacket(None, None, packet)


        if _typ == PacketType.DEV_LOGIN:
            format_ = NamedTuple("LoginPacket", [
                ('imei', str),
                ("password", str)
            ])

        elif _typ == PacketType.DEV_EXTENDED_DATA:
            format_ = NamedTuple("FullDataPacket", [
                ('date', int),
                ("time", int),
                ("lat_deg", int),
                ("lat_sign", str),
                ("lon_deg", int),
                ("lon_sign", str),
                ("speed", int),
                ("course", int),
                ("alt", int),
                ("sats", int),
                ("hdop", int),
                ("inputs", int),
                ("outputs", int),
                ("adc", int),
                ("ibutton", int),
                ("params", int),
            ])

        elif _typ == PacketType.DEV_SHORT_DATA:
            format_ = NamedTuple("FullDataPacket", [
                ('date', int),
                ("time", int),
                ("lat_deg", int),
                ("lat_sign", str),
                ("lon_deg", int),
                ("lon_sign", str),
                ("speed", int),
                ("course", int),
                ("alt", int),
                ("sats", int),
            ])

        elif _typ == PacketType.DEV_PING:
            format_ = NamedTuple("PingPacket", [])

        # elif _typ == PacketType.DEV_BLACKBOX:
        #     print(params.split("|"))
        #     params =

        else:
            format_ = NamedTuple("UndefinedPacket", [])

        _kwargs = format_(*_params)._asdict()

        return DevPacket(_typ, None, packet, **_kwargs)

    def parse_upcoming_packet(self, packet: bytes) -> Optional[DevPacket]:
        try:
            _packet = packet.decode('ascii')
        except UnicodeDecodeError:
            return DevPacket(None, LoginResponseCode.ERROR, packet)

        match = re.match(r"#(\w+)#(\d+(.\d)?)?", _packet, re.IGNORECASE)
        if not match:
            return DevPacket(None, LoginResponseCode.ERROR, packet)

        typ, code, subcode, *other = match.groups()
        print(typ, code, subcode, *other)

        try:
            _typ = PacketType(typ)
        except KeyError:
            return DevPacket(None, None, packet)

        if _typ == PacketType.SRV_EXTENDED_DATA_RESPONSE:
            code = ExtendedDataResponseCode(code)

        elif _typ == PacketType.SRV_SHORT_DATA_RESPONSE:
            print(other.split(";"))

            code = ShortDataResponseCode(code)

        elif _typ == PacketType.SRV_LOGIN_RESPONSE:
            code = LoginResponseCode(code)

        elif _typ == PacketType.SRV_BLACKBOX_RESPONSE:
            code = code

        return DevPacket(_typ, code, packet)


if __name__ == "__main__":
    p = Protocol()
    r = p.parse_upcoming_packet(b"#AD#15.1\r\n")
    print(r)
    r = p.parse_upcoming_packet(b"#AL#1\r\n")
    print(r)
    r = p.parse_upcoming_packet(b'#AB#\r\n')
    print(r)

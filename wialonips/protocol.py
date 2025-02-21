import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Literal, Union, NamedTuple, Dict, List

from wialonips.crc16 import crc16, crc16_to_ascii_hex

INCOMING_PACKET_PATTERN = r"^#(\w+)#(.*?)(0x[0-9a-fA-F]+)?\r\n$"
INCOMING_PACKET_REGEX = re.compile(INCOMING_PACKET_PATTERN, re.IGNORECASE)

LAT_SIGN = Literal['N', 'S']
LON_SIGN = Literal['E', 'W']

SEPARATOR = ";"
NOT_AVAILABLE = "NA"
ALARM_PARAM = "SOS"
# LBS_MMC_PARAM = "mcc%d"
LBS_MMC_PARAM = "mcc"
# LBS_MNC_PARAM = "mnc%d"
LBS_MNC_PARAM = "mnc"
# LBS_LAC_PARAM = "lac%d"
LBS_LAC_PARAM = "lac"
# LBS_CELL_ID_PARAM = "cell_id%d"
LBS_CELL_ID_PARAM = "cell_id"
WIFI_MAC_PARAM = "wifi_mac_%d"
WIFI_RSSI_PARAM = "wifi_rssi_%d"

ParamValueTypes = {
    1: int,
    2: float,
    3: str,
}


class LoginBody(NamedTuple):
    imei: str
    password: str


class PingBody(NamedTuple):
    pass


class ShortDataBody(NamedTuple):
    date: int
    time: int
    lat_deg: int
    lat_sign: str
    lon_deg: int
    lon_sign: str
    speed: int
    course: int
    alt: int
    sats: int


class FullDataBody(NamedTuple):
    date: int
    time: int
    lat_deg: int
    lat_sign: str
    lon_deg: int
    lon_sign: str
    speed: int
    course: int
    alt: int
    sats: int
    hdop: int
    inputs: int
    outputs: int
    adc: int
    ibutton: int
    params: int


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


def parse_datetime(date_str: str, time_str: str) -> datetime:
    """Convert YYMMDD and HHMMSS into a datetime object."""
    return datetime.strptime(date_str + time_str, "%y%m%d%H%M%S")


def dms_to_decimal(deg_min: str, sign: Union[LAT_SIGN, LON_SIGN]) -> float:
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
    type: Optional[PacketType] = None
    code: Optional[Any] = None
    raw: Optional[bytes] = None

    imei: Optional[str] = None
    password: Optional[str] = None

    date: Optional[int] = None
    time: Optional[int] = None
    lat_deg: Optional[float] = None
    lat_sign: Optional[LAT_SIGN] = None
    lon_deg: Optional[float] = None  # GGGMM.MM
    lon_sign: Optional[LON_SIGN] = None
    speed: Optional[int] = None
    course: Optional[int] = None
    alt: Optional[int] = None
    sats: Optional[int] = None

    hdop: Optional[float] = 1.0
    inputs: Optional[int] = None
    outputs: Optional[int] = None
    adc: Optional[List[float]] = field(default_factory=list)
    ibutton: Optional[str] = None

    alarm: bool = False

    params: Dict[str, str] = field(default_factory=dict)

    lbs: Dict[str, Union[float, int]] = field(init=False, default_factory=dict)

    def __post_init__(self):
        self._parse_adc()
        self._parse_params()

    @classmethod
    def parse_from_bytes(cls, packet: bytes) -> "DevPacket":
        try:
            _packet = packet.decode('ascii')
        except UnicodeDecodeError:
            return DevPacket(None, LoginResponseCode.ERROR, packet)

        match = INCOMING_PACKET_REGEX.fullmatch(_packet)

        if not match:
            print("Couldn't parse incoming packet")
            return DevPacket(None, LoginResponseCode.ERROR, packet)

        typ, body, crc = match.groups()
        print(typ, body, crc)

        # if self.version.startswith("2") and crc is not None:
        if crc is not None:
            cls.crc_check(body.encode('ascii'), crc.encode('ascii'))

        params: list[str] = [None if value == NOT_AVAILABLE else value for value in body.split(";")]

        try:
            _typ = PacketType(typ)
        except KeyError:
            return cls(None, None, packet)

        if _typ == PacketType.DEV_LOGIN:
            format_ = LoginBody

        elif _typ == PacketType.DEV_EXTENDED_DATA:
            format_ = FullDataBody

        elif _typ == PacketType.DEV_SHORT_DATA:
            format_ = ShortDataBody

        elif _typ == PacketType.DEV_PING:
            format_ = PingBody

        # elif _typ == PacketType.DEV_BLACKBOX:
        #     print(params.split("|"))
        #     params =

        else:
            format_ = NamedTuple("UndefinedPacket", [])

        _kwargs = format_(*params)._asdict()

        return cls(_typ, None, packet, **_kwargs)

    @classmethod
    def crc_check(cls, body: bytes, expected_crc: bytes):
        if cls.crc_body(body) != expected_crc:
            raise ValueError("CRC check failed")

    @classmethod
    def crc_body(cls, body: bytes):
        crc = crc16(body)
        return crc16_to_ascii_hex(crc)

    def _parse_adc(self):
        if self.adc and isinstance(self.adc, str):
            try:
                self.adc = [float(adc) for adc in self.adc.split(",")]
            except ValueError:
                print("Invalid ADC format")

    def _parse_params(self) -> None:
        if self.params and isinstance(self.params, str):
            params = self.params.split(",")
            _params = {}

            for param in params:
                key, typ, value = param.split(":")

                if typ.isdigit() and (_typ := ParamValueTypes.get(int(typ))):
                    try:
                        _params[key] = None if value == NOT_AVAILABLE else _typ(value)
                    except (ValueError, TypeError):
                        print(f"Invalid param format {key}.{_typ}.{value}")
                        _params[key] = value

            # if alarm
            if ALARM_PARAM in _params:
                self.alarm = _params.pop(ALARM_PARAM) == 1

            # if lbs
            for key, value in _params.items():
                if key.startswith((LBS_MMC_PARAM, LBS_MNC_PARAM, LBS_LAC_PARAM, LBS_CELL_ID_PARAM)):
                    try:
                        self.lbs[key] = _params.pop(key)
                    except (ValueError, TypeError):
                        print(f"Invalid LBS Params format {key}: {value}")

            self.params = _params

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

    @property
    def inputs_list(self):
        return self._map_io(self.inputs)

    @property
    def outputs_list(self):
        return self._map_io(self.outputs)

    @staticmethod
    def _map_io(field):
        if field:
            if isinstance(field, str) and field.isdigit():
                mask = int(field)
                return [int(bit) for bit in bin(mask)[2:].zfill(32)][::-1]
            elif isinstance(field, list) and all(isinstance(item, int) for item in field):
                return field
        return []


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
                          lat_sign=Optional[LAT_SIGN],
                          lon_deg: Optional[float] = None,  # GGGMM.MM
                          lon_sing=Optional[LON_SIGN],
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
        return DevPacket.parse_from_bytes(packet)

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
    # r = p.parse_upcoming_packet(b"#AD#15.1\r\n")
    # print(r)
    # r = p.parse_upcoming_packet(b"#AL#1\r\n")
    # print(r)
    # r = p.parse_upcoming_packet(b'#AB#\r\n')
    # print(r)

    if __name__ == "__main__":
        head = b'#SD#'
        body = b'210225;092758;5355.09260;N;02732.40990;E;0;0;300;7'
        crc = p.crc_data(body)
        end = b'\r\n'
        buf = head + body + crc + end
        print(buf)

        pack = p.parse_incoming_packet(head + body + end)
        print(pack)

        pack = p.parse_incoming_packet(buf)
        print(pack)

        buf = b'#D#210225;095553;5355.09260;N;02732.40990;E;0;0;300;7;1;2;18432;5,0;NA;a:1:5,b:3:NA\r\n'
        print(p.parse_incoming_packet(buf))

import re
from enum import Enum
from typing import Literal, NamedTuple

LAT_SIGN = Literal['N', 'S']
LON_SIGN = Literal['E', 'W']

# INCOMING_PACKET_PATTERN = r"^#(\w+)#(.*?)(;(0x[0-9a-fA-F]+))?\r\n$"
INCOMING_PACKET_PATTERN = r"^#(\w+)#(.*?(?=;0x[0-9a-fA-F]+)|.*?)?(?:;(0x[0-9a-fA-F]+))?\r\n$"

INCOMING_PACKET_REGEX = re.compile(INCOMING_PACKET_PATTERN, re.IGNORECASE)

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

class UndefinedPacket(NamedTuple):
    pass

class LoginBody(NamedTuple):
    protocol_version: str
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
    UNKNOWN = "UNKNOWN"

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


class Position(NamedTuple):
    latitude: float
    longitude: float
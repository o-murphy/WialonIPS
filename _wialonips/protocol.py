from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Union, Dict, List

from _wialonips.crc16 import crc16
from _wialonips.types import *
from _wialonips.utils import parse_datetime, dms_to_decimal, decimal_to_ddmm


@dataclass
class DevPacket:
    type: PacketType
    protocol_version: Optional[int] = None
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
            return DevPacket(type=PacketType.UNKNOWN, code=LoginResponseCode.ERROR, raw=packet)

        match = INCOMING_PACKET_REGEX.fullmatch(_packet)

        if not match:
            print("Couldn't parse incoming packet")
            return cls(PacketType.UNKNOWN, code=LoginResponseCode.ERROR, raw=packet)

        # typ, body, _, crc = match.groups()
        typ, body, _params, crc = match.groups()
        print(typ, body, _params, crc)

        # if self.version.startswith("2") and crc is not None:
        if crc is not None:
            cls.crc_check(body.encode('ascii'), crc.encode('ascii'))

        params: list[str] = [None if value == NOT_AVAILABLE else value for value in _params.split(";")]

        try:
            _typ = PacketType(typ)
        except KeyError:
            return cls(PacketType.UNKNOWN, code=None, raw=packet)

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
            format_ = UndefinedPacket

        _kwargs = format_(*params)._asdict()
        return cls(_typ, code=None, raw=packet, **_kwargs)

    @classmethod
    def crc_check(cls, body: bytes, expected_crc: bytes):
        print(cls.crc_body(body), expected_crc)
        if cls.crc_body(body) != expected_crc:
            raise ValueError("CRC check failed")

    @classmethod
    def crc_body(cls, body: bytes):
        return f"{crc16(body):0X}".encode("ascii")

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
        return datetime.now()

        # raise ValueError("Unable to parse date and time")

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

    def __init__(self, version="2.2"):
        self.version = version

    def build_login_packet(self, imei, password):
        return self.build_packet(PacketType.DEV_LOGIN, data=[imei, password])

    def build_data_packet(self,
                          date_time: Optional[datetime] = None,
                          lat: Optional[float] = None,
                          lon: Optional[float] = None,
                          speed: Optional[int] = None,
                          course: Optional[int] = None,
                          alt: Optional[int] = None,
                          sats: Optional[int] = None,
                          # hdop: Optional[float] = 1.0,
                          hdop: Optional[float] = None,
                          inputs: Optional[int] = None,
                          outputs: Optional[int] = None,
                          adc: Optional[list[float]] = None,
                          ibutton: Optional[str] = None,
                          alarm: bool = False,
                          **params,
                          ):

        if date_time is not None:
            date = date_time.strftime("%d%m%y")
            time = f'{date_time.strftime("%H%M%S")}.{date_time.microsecond * 1000:09d}'
        else:
            date, time = None, None

        if course is not None and not (0 <= course < 360):
            course = None

        if speed is not None and speed < 0:
            speed = None

        if sats is not None and sats < 0:
            sats = None

        if lat is None or lon is None:
            lat_deg, lon_deg = None, None
            lat_sign, lon_sign = None, None
        else:
            lat_deg, lat_sign = decimal_to_ddmm(lat, True)
            lon_deg, lon_sign = decimal_to_ddmm(lon, False)

        if adc:
            adc = ",".join([_stringify(i) for i in adc])

        if alarm:
            params[ALARM_PARAM] = 1

        def param_type(param):
            if isinstance(param, str):
                return 3
            if isinstance(param, int):
                return 1
            if isinstance(param, float):
                return 2
            return 0

        params = ','.join([f"{_stringify(k)}:{param_type(v)}:{_stringify(v)}" for k, v in params.items()])

        data = [_stringify(i) for i in (
            date, time, lat_deg, lat_sign, lon_deg, lon_sign,
            speed, course, alt, sats,
            hdop, inputs, outputs, adc, ibutton,
            params
        )]

        return self.build_packet(PacketType.DEV_EXTENDED_DATA, data=data)

    def build_short_data_packet(self,
                                date_time: Optional[datetime] = None,
                                lat: Optional[float] = None,
                                lon: Optional[float] = None,
                                speed: Optional[int] = None,
                                course: Optional[int] = None,
                                alt: Optional[int] = None,
                                sats: Optional[int] = None):

        if date_time is not None:
            date = date_time.strftime("%d%m%y")
            time = f'{date_time.strftime("%H%M%S")}.{date_time.microsecond * 1000:09d}'
        else:
            date, time = None, None

        if course is not None and not (0 <= course < 360):
            course = None

        if speed is not None and speed < 0:
            speed = None

        if sats is not None and sats < 0:
            sats = None

        if lat is None or lon is None:
            lat_deg, lon_deg = None, None
            lat_sign, lon_sign = None, None
        else:
            lat_deg, lat_sign = decimal_to_ddmm(lat, True)
            lon_deg, lon_sign = decimal_to_ddmm(lon, False)

        data = [_stringify(i) for i in (date, time, lat_deg, lat_sign, lon_deg, lon_sign,
                                        speed, course, alt, sats)]
        return self.build_packet(PacketType.DEV_SHORT_DATA, data=data)

    def build_black_box_packet(self, packets):
        data = "|".join(packets)
        return self.build_packet(PacketType.DEV_BLACKBOX, data=[data])

    def build_packet(self, packet_type: PacketType, data=None) -> bytes:
        header = f"#{packet_type.value}#"
        body = (SEPARATOR.join(data) + ";").encode()
        crc = DevPacket.crc_body(body)
        return header.encode("ascii") + body + crc + b"\r\n"

    def parse_incoming_packet_from_dev(self, packet: bytes) -> Optional[DevPacket]:
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
        buf = b'#D#210225;095553;5355.09260;N;02732.40990;E;0;0;300;7;1;2;18432;5,0;NA;a:1:5,b:3:NA\r\n'
        print(p.parse_incoming_packet_from_dev(buf))

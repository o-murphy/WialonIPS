import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, Callable


class Priority(int, Enum):
    NONE = 0
    LOW = 1
    HIGH = 2
    PANIC = 3


class Operand(int, Enum):
    ON_EXIT = 0
    ON_ENTRANCE = 1
    ON_BOTH = 2
    MONITORING = 3
    ON_HYSTERESIS = 4
    ON_CHANGE = 5
    ON_DELTA_CHANGE = 6  # uses >= hi_lvl


POSITIONAL_PARAMS = (
    "date",
    "time",
    "lat_deg",
    "lat_sign",
    "lon_deg",
    "lon_sign",
    "speed",
    "course",
    "alt",
    "sats",
    
    "hdop",
    "ibutton",
)

POSITIONAL_ELEMENTS = {
    k: {"priority": Priority.LOW, "operand": Operand.MONITORING}
    for k in POSITIONAL_PARAMS
}


AUTH_PARAMS = ("ver", "imei", "password", 'host', 'port')

AUTH_ELEMENTS = {
    k: {"priority": Priority.NONE, "operand": Operand.MONITORING} for k in AUTH_PARAMS
}

AUTH_ELEMENTS['ver']['value'] = "2.0"
AUTH_ELEMENTS['imei']['value'] = "wips"
AUTH_ELEMENTS['password']['value'] = "wips"
AUTH_ELEMENTS['host']['value'] = "193.193.165.165"
AUTH_ELEMENTS['port']['value'] = 20332

FIXED_PARAMS = {
    'SOS': {
        'operand': Operand.ON_CHANGE,
        'priority': Priority.HIGH,
        'event_only': True,
    },
    'text': {
        'operand': Operand.ON_CHANGE,
        'priority': Priority.HIGH,
        'event_only': True,
    },
}


def _str(i):
    return 'NA' if i is None else str(i)


@dataclass(order=True)
class Record:
    priority: Priority = Priority.LOW
    positional: dict[str, Any] = field(default_factory=dict)
    io: tuple[int, int] = 0
    adc: list[float] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    
    @property
    def short(self):
        return ";".join(_str(i) for i in tuple(self.positional.values())[:10]) + ";"
        
    @property
    def full(self):
        
        def t(v):
            if isinstance(v, int):
                return 1
            elif isinstance(v, float):
                return 2
            return 3

        positional = ";".join(_str(i) for i in tuple(self.positional.values())[:10])
        hdop = _str(self.positional.get('hdop'))
        ibutton = _str(self.positional.get('ibutton'))
        io = ";".join(_str(i) for i in self.io)
        adc = ",".join(_str(i) for i in self.adc) if self.adc else _str(None)
        par = ",".join(f'{k}:{t(v)}:{_str(v)}' for k, v in self.params.items())

        return ";".join((
            positional,
            hdop,
            io, 
            adc, 
            ibutton,
            par
        )) + ";"


@dataclass
class IOElement:
    uid: uuid.UUID = field(init=False, default_factory=lambda: uuid.uuid4().hex[:8])
    value: Any = None
    lo_lvl: float = 0
    hi_lvl: float = 1
    event_only: bool = False  # only for named params
    priority: Priority = Priority.NONE  # only for named params
    operand: Operand = Operand.MONITORING
    # avg_const: int = 10 # 1 = 0.1s

    def __hash__(self):
        """Hash based only on the UUID."""
        return hash(self.uid)

    def upd(self, v):
        op = self.operand

        if op is Priority.NONE:
            return False

        prev = self.value
        if prev == v:
            return False

        self.value = v

        if op is Operand.MONITORING:
            return False

        if op is Operand.ON_CHANGE:
            return True

        if not isinstance(v, (float, int)):
            return

        lo, hi = self.lo_lvl, self.hi_lvl

        is_exit = lo <= prev <= hi and v > hi or v < lo

        if op is Operand.ON_EXIT:
            return is_exit

        is_entrance = lo < v < hi and prev >= hi or prev <= lo

        if op is Operand.ON_ENTRANCE:
            return is_entrance

        if op is Operand.ON_BOTH:
            return is_exit or is_entrance

        if op is Operand.ON_DELTA_CHANGE:
            if abs(prev - v) >= self.hi_lvl:
                return True
            self.value = prev
            return False


def els2bitmask(els):
    bitmask = 0
    for i, el in enumerate(els):
        # If x > 0, set the bit at position i to 1; otherwise, set it to 0
        if el.value is None:
            continue
        if el.value > 0:
            bitmask |= (
                1 << i
            )  # Shift 1 to the i-th position and use bitwise OR to set the bit
    return bitmask


def not_event_only(els):
    return [el for el in els if not el.event_only]


@dataclass
class IOObserver:
    positional: dict[str, IOElement] = field(init=False, default_factory=dict)
    inputs: list[IOElement] = field(init=False, default_factory=list)
    outputs: list[IOElement] = field(init=False, default_factory=list)
    adc: list[IOElement] = field(init=False, default_factory=list)
    params: dict[str, IOElement] = field(init=False, default_factory=dict)

    _evt_only: list[IOElement] = field(init=False)

    on_event: Optional[Callable[[Record], None]] = None

    def __post_init__(self):
        self.params.update({k: IOElement(**item) for k, item in AUTH_ELEMENTS.items()})
        self.params.update({k: IOElement(**item) for k, item in FIXED_PARAMS.items()})
        self.positional.update({k: IOElement(**item) for k, item in POSITIONAL_ELEMENTS.items()})
        self.clear_event()

    def clear_event(self):
        self._evt_only = []

    def event(self, priority=Priority.LOW):
        def filter_param(item):
            k, el = item
            if el.priority > Priority.NONE:
                if not el.event_only:
                    return True
                if el in self._evt_only:
                    return True
            return False

        params_els = filter(filter_param, self.params.items())
        record = Record(
            priority,
            {k: el.value for k, el in self.positional.items()},
            self.io,
            [el.value for el in self.adc],
            {k: el.value for k, el in params_els},
        )
        self.clear_event()

        if callable(self.on_event):
            self.on_event(record)

    @property
    def io(self):
        if self.inputs:
            inp = els2bitmask(self.inputs)
        else:
            inp = None
        if self.outputs:
            out = els2bitmask(self.outputs)
        else:
            out = None
        return inp, out

    def upd_input(self, bit, v):
        if 0 <= bit <= len(self.inputs):
            el = self.inputs[bit]
            if el.priority is Priority.NONE:
                return

            if el.upd(v) and el.priority > Priority.LOW:
                self.event(el.priority)

    def upd_output(self, bit, v):
        if 0 <= bit <= len(self.outputs):
            el = self.outputs[bit]
            if el.priority is Priority.NONE:
                return

            if el.upd(v) and el.priority > Priority.LOW:
                self.event(el.priority)

    def upd_adc(self, idx, v):
        if 0 <= idx <= len(self.adc):
            el = self.adc[idx]
            if el.priority is Priority.NONE:
                return

            if el.upd(v) and el.priority > Priority.LOW:
                self.event(el.priority)

    def upd_param(self, key, v):
        if key in self.params:
            el = self.params[key]
            if el.priority is Priority.NONE:
                return

            if el.upd(v):
                if el.event_only:
                    self._evt_only.append(el)

                if el.priority > Priority.LOW:
                    self.event(el.priority)
                    
    def upd_params(self, **kwargs):
        priority = Priority.NONE
        for key, v in kwargs.items():
            if key in self.params:
                el = self.params[key]
                if el.priority is Priority.NONE:
                    continue

                if el.upd(v):
                    if el.event_only:
                        self._evt_only.append(el)
                    
                if el.priority > priority:
                    priority = el.priority

        if priority > Priority.LOW:
            self.event(priority)
            
    def upd_positional(self, *args, **kwargs):
        priority = Priority.LOW
        
        for i, v in enumerate(args):
            if 0 <= i < len(self.positional.values()):
                
                el = tuple(self.positional.values())[i]
                
                el.upd(v)
                
                if el.priority > priority:
                    priority = el.priority
        
        for key, v in kwargs.items():
            if key in self.positional:
                el = self.positional[key]
                
                el.upd(v)
                
                if el.priority > priority:
                    priority = el.priority
                    
        if priority > Priority.LOW:
            self.event(priority)


if __name__ == "__main__":
    o = IOObserver(on_event=print)

    for i in range(32):
        out = IOElement()
        o.outputs.append(out)

    for i in range(32):
        inp = IOElement()
        o.inputs.append(inp)

    for i in range(2):
        adc = IOElement()
        o.adc.append(adc)

    for i in range(2):
        p = IOElement(priority=Priority.LOW)
        o.params[f"param{i+1}"] = p

    o.event()
    o.upd_param("SOS", 1)
    o.upd_params(SOS=0, text='hello')
    o.upd_positional(220225)
    o.event()


import random
import re
import socket
import threading
import time
from queue import Queue
from threading import Thread

# import bat
import dt
import geo
from WialonIPS.fsm import IOElement, Operand, Priority
from blackbox import BlackBox
from crc16 import crc16
from fsm import IOObserver

__version__ = "2.0"

ENCODING = "ascii"

NOT_ALLOWED = "NA"

LOGIN_BODY_FMT = "%s;{imei};{password};" % __version__
LOGIN_QUERY_FMT = "#L#{body}{crc}\r\n"
LOGIN_ANSWER_REGEX = re.compile("^#AL#(\d+)\r\n$", re.IGNORECASE)

LOGIN_ANSWER_STATUS = {
    "0": "Connection rejected by server",
    "1": "Success",
    "01": "Password error",
    "10": "CRC Check error",
}

COORDS_QUERY_FMT = "#SD#{body}{crc}\r\n"
DATA_QUERY_FMT = "#D#{body}{crc}\r\n"
COORDS_ANSWER_REGEX = re.compile("^#ASD#(\d+)\r\n$", re.IGNORECASE)
DATA_ANSWER_REGEX = re.compile("^#AD#(\d+)\r\n$", re.IGNORECASE)


def crc(body):
    return f"{crc16(body):0X}"


def join_fields(*fields):
    print(fields)
    return ";".join(NOT_ALLOWED if f is None else str(f) for f in fields) + ";"


def join_params(**params):
    strings = []
    for k, v in params.items():
        if v is None:
            pass
        elif isinstance(v, int):
            strings.append(f"{k}:{1}:{v}")
        elif isinstance(v, float):
            strings.append(f"{k}:{2}:{v}")
        elif isinstance(v, str):
            strings.append(f"{k}:{3}:{v}")
    return ",".join(strings)


class Device:
    def __init__(self, observer, blackbox):
        self.observer = observer or IOObserver()
        self.blackbox = blackbox or BlackBox()
        self.observer.on_event = self.blackbox.on_record

        self.socket = None
        self.resp_queue = Queue()

    def login(self):
        body = LOGIN_BODY_FMT.format(
            imei=self.observer.params['imei'].value or NOT_ALLOWED,
            password=self.observer.params['password'].value or NOT_ALLOWED
        )
        self.send(LOGIN_QUERY_FMT.format(body=body, crc=crc(body.encode(ENCODING))))
        match = self.wait_resp(LOGIN_ANSWER_REGEX, timeout=1)

        if match:
            code = match.group(1)
            if code == "1":
                return True
            msg = LOGIN_ANSWER_STATUS.get(code, "Undefined")
            print("Err:", code, msg)
        else:
            print("Err:", -1, "No response")
        return False

    @property
    def coords(self):
        ts, lat, lon, *other = geo.get()

        cdt = dt.dt() if ts is None else dt.utc2dt(ts)
        return (*cdt, *geo.dec2ddmm(lat, True), *geo.dec2ddmm(lon, False), *other)

    def send(self, message):
        if not self.socket:
            raise Exception("Socket is not opened")

        buf = message.encode(ENCODING)

        self.socket.send(buf)
        print(">>>", buf)

    def wait_resp(self, pattern, timeout=1):
        t = 0
        while t < timeout:
            try:
                data = self.resp_queue.get()
                # data = self.resp_queue.queue[0]

                match = pattern.fullmatch(data.decode(ENCODING))
                if match:
                    # self.resp_queue.get()
                    return match
                self.resp_queue.put(data)
            except Exception:
                pass
            time.sleep(t)
            t += 1

        return None

    def open(self):
        """Open a persistent socket connection."""
        if self.socket is None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.observer.params['host'].value, self.observer.params['port'].value))
            print("Socket opened")
        else:
            print("Socket already open")

    def close(self):
        if self.socket:
            self.socket.close()
            self.socket = None
            print("Socket closed")

    def send_records(self):
        while len(self.blackbox.queue) > 0:
            for rec in self.blackbox.peek(1):
                body = rec.full
                packet = DATA_QUERY_FMT.format(
                    body=body,
                    crc=crc(body.encode(ENCODING))
                )
                self.send(packet)
                if match := self.wait_resp(DATA_ANSWER_REGEX, timeout=1):
                    code = match.group(1)
                    if code == "1":
                        self.blackbox.confirm(1)

    def write_loop(self):
        while self.socket:
            try:
                self.send_records()
                time.sleep(self.blackbox.timeout)
            except Exception as exc:
                print(exc)
                self.close()

    def read_loop(self):
        while self.socket:
            try:
                data = self.socket.recv(1024)
                if data:
                    print("<<<", data)
                    self.resp_queue.put(data)
            except Exception as exc:
                print(exc)
                self.close()

    def monitor(self):

        def repeat_task(interval, func, *args):
            """Runs a function repeatedly at a given interval in a separate thread."""
            stop_event = threading.Event()

            def loop():
                while not stop_event.is_set():
                    func(*args)
                    stop_event.wait(interval)  # Wait for the given interval or stop signal

            thread = threading.Thread(target=loop, daemon=True)
            thread.start()
            return stop_event  # Allows stopping the thread if needed

        def random_param1():
            observer.upd_param('param1', random.randrange(1, 10))

        stop_t1 = repeat_task(5, observer.upd_positional, *device.coords)
        stop_t2 = repeat_task(10, observer.event)
        stop_t3 = repeat_task(15, random_param1)

    def run_poling(self):
        monitor_thread = threading.Thread(target=self.monitor, daemon=True)

        while True:
            try:
                if not monitor_thread.is_alive():
                    monitor_thread.start()

                if not self.socket:
                    self.open()
                    if self.socket:
                        Thread(target=self.read_loop, daemon=True).start()
                        if self.login():
                            Thread(target=self.write_loop, daemon=True).start()
                        else:
                            self.close()

            except Exception as exc:
                ...


if __name__ == '__main__':
    observer = IOObserver()
    observer.params['param1'] = IOElement(
        operand=Operand.ON_CHANGE,
        priority=Priority.HIGH,
        event_only=True
    )
    observer.upd_positional(ibutton="wispdriver")
    blackbox = BlackBox()
    device = Device(observer, blackbox)

    try:
        device.run_poling()
    finally:
        device.close()
        print('Done')

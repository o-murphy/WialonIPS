from datetime import datetime

def dt(now = None):
    if now is None:
        now = datetime.now()
    date = now.strftime("%d%m%y")
    time = f'{now.strftime("%H%M%S")}.{now.microsecond * 1000:09d}'
    return date, time

def utc2dt(timestamp):
    now = datetime.utcfromtimestamp(timestamp)
    return dt(now)


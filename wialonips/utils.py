from datetime import datetime, timedelta
from typing import Union, Tuple

from wialonips.types import LAT_SIGN, LON_SIGN


def parse_datetime_with_nanoseconds(date_str: str, time_str: str):
    # Remove the fractional part for datetime parsing (seconds only)
    time_str = time_str.split('.')[0]  # Take only the part before the dot for datetime parsing
    dt = datetime.strptime(date_str + time_str, "%y%m%d%H%M%S")

    # Extract the fractional part (nanoseconds)
    fraction = time_str.split('.')[1] if '.' in time_str else '0'
    nanoseconds = int(fraction.ljust(9, '0'))  # Pad with zeros to make it nanoseconds (9 digits)

    # Add the nanoseconds as a timedelta
    nanosecond_delta = timedelta(microseconds=nanoseconds / 1000)  # Convert nanoseconds to microseconds

    # Add the nanosecond delta to the datetime
    dt_with_nanoseconds = dt + nanosecond_delta

    return dt_with_nanoseconds


def parse_datetime(date_str: str, time_str: str) -> datetime:
    """Convert YYMMDD and HHMMSS into a datetime object."""
    # return datetime.strptime(date_str + time_str, "%y%m%d%H%M%S")
    return parse_datetime_with_nanoseconds(date_str, time_str)


def decimal_to_ddmm(decimal: float, is_latitude: bool) -> Tuple[str, Union[LAT_SIGN, LON_SIGN]]:
    """Convert decimal coordinates to DDMM.MM (latitude) or DDDMM.MM (longitude) with a literal sign."""
    # Determine the sign based on the value of the coordinate
    if is_latitude:
        sign = 'S' if decimal < 0 else 'N'
    else:
        sign = 'W' if decimal < 0 else 'E'

    # Take the absolute value of the decimal coordinate
    decimal = abs(decimal)

    # Calculate degrees
    degrees = int(decimal)

    # Calculate minutes
    minutes = (decimal - degrees) * 60

    # For latitude, use 2 digits for degrees, for longitude, use 3 digits for degrees
    if is_latitude:
        degree_format = "{:02d}"  # Latitude: 2 digits for degrees
    else:
        degree_format = "{:03d}"  # Longitude: 3 digits for degrees

    # Format the output to DDMM.MM or DDDMM.MM
    # ddmm = f"{degree_format.format(degrees)}{minutes:05.2f}"
    ddmm = f"{degree_format.format(degrees)}{minutes:05.6f}"

    # Return the result with the sign
    return ddmm, sign


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
def dec2ddmm(decimal, is_latitude):
    if decimal is None:
        return None, None
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


try:
    import location


    def get():
        location.start_updates()  # Start location updates
        coords = location.get_location()  # Get current location
        location.stop_updates()  # Stop updates to save battery
        print(coords)
        if coords:
            latitude = coords['latitude']
            longitude = coords['longitude']
            print(f"Latitude: {latitude}, Longitude: {longitude}")

            speed = coords['speed']  # Speed in meters per second
            course = coords['course']  # Course in degrees (0 = North, 90 = East)
            altitude = coords['altitude']  # Altitude in meters
            h_accuracy = coords['horizontal_accuracy']
            v_accuracy = coords['vertical_accuracy']
            print(f"Speed: {speed} m/s")
            print(f"Course: {course}°")
            print(f"Altitude: {altitude} meters")

            course = int(course) if 0 <= course < 359 else None
            speed = int(speed) if speed >= 0 else None
            altitude = int(altitude) if altitude else None
            h_accuracy = int(h_accuracy) if h_accuracy else None
            v_accuracy = int(v_accuracy) if v_accuracy else None

            satellites = None
            timestamp = coords['timestamp']

            return timestamp, latitude, longitude, speed, course, altitude, satellites, h_accuracy, v_accuracy
        else:
            print("Failed to get location")
            return [None] * 9

except ImportError as e:
    import geocoder


    def get():
        try:
            g = geocoder.ip('me')
            latitude, longitude = g.latlng
        except Exception as e:
            latitude, longitude = None, None

        timestamp, speed, course, altitude, satellites, h_accuracy, v_accuracy = (None, None, None,
                                                                                  None, None, None, None)

        return timestamp, latitude, longitude, speed, course, altitude, satellites, h_accuracy, v_accuracy

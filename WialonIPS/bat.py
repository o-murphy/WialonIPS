try:
    from objc_util import ObjCClass

    def bat():


        UIDevice = ObjCClass('UIDevice')
        device = UIDevice.currentDevice()
        device.setBatteryMonitoringEnabled_(True)  # Enable battery monitoring

        battery_level = device.batteryLevel() * 100  # Convert to percentage
        #print(f"Battery Level: {battery_level:.0f}%")
        return battery_level

except Exception as e:
    def bat():
        return 100.0

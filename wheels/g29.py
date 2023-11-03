import hid

VENDOR_ID = 1133
PRODUCT_ID = 49743


class G29:
    def __init__(self):
        self.device = None
        
    def connect(self):
        try:
            self.device = hid.Device(VENDOR_ID, PRODUCT_ID)
        except hid.HIDException:
            return False
        return True
    
    def leds_rpm(self, percent):
        if percent > 84:
            leds = '11111'
        elif percent > 69:
            leds = '1111'
        elif percent > 39:
            leds = '111'
        elif percent > 19:
            leds = '11'
        elif percent > 4:
            leds = '1'
        else:
            leds = '0'
        msg = [0xf8, 0x12, int(leds, 2), 0x00, 0x00, 0x00, 0x01]
        self.device.write(bytes(msg))
        
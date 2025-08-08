from wheels.base import BaseWheel

class HIDClassic(BaseWheel):
    def _led_report(self, bits: int):
        # Classic hid format: [0xF8, 0x12, bits, 0, 0, 0, 1]
        return (0xF8, 0x12, bits, 0x00, 0x00, 0x00, 0x01)

class HIDpp(BaseWheel):
    def _post_connect_setup(self):
        # put wheel into “direct LED” mode once
        self._dev.write(bytes((0x11, 0xFF, 0x12, 0x31, 0x00)))

    def _led_report(self, bits: int):
        # G923 format: [0x11, 0xFF, 0x12, 0x51, 0, 5, bits]
        return (0x11, 0xFF, 0x12, 0x51, 0x00, 0x05, bits)

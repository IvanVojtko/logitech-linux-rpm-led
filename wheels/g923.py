from wheels.base import BaseWheel


class G923(BaseWheel):
    PRODUCT_IDS = (0xC26E, 0xC267)   # Xbox / PS4 variants

    def _post_connect_setup(self):
        # put wheel into “direct LED” mode once
        self._dev.write(bytes((0x11, 0xFF, 0x12, 0x31, 0x00)))

    def _led_report(self, bits: int):
        # G923 format: [0x11, 0xFF, 0x12, 0x51, 0, 5, bits]
        return (0x11, 0xFF, 0x12, 0x51, 0x00, 0x05, bits)

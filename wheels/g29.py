from wheels.base import BaseWheel


class G29(BaseWheel):
    PRODUCT_IDS = (0xC24F, 0xC260)   # PS3 / PS4 variants

    def _led_report(self, bits: int):
        # G29 format: [0xF8, 0x12, bits, 0, 0, 0, 1]
        return (0xF8, 0x12, bits, 0x00, 0x00, 0x00, 0x01)

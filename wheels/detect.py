import hid
from wheels.wheels import G29
from wheels.wheels import G923xbox
from wheels.wheels import G923ps4
from wheels.base import BaseWheel

# Register every VID/PID with its class
DEVICE_MAP: dict[tuple[int, int], type[BaseWheel]] = {}
for cls in (G29, G923xbox, G923ps4):
    for pid in cls.PRODUCT_IDS:
        DEVICE_MAP[(cls.VENDOR_ID, pid)] = cls


def find_wheel() -> BaseWheel | None:
    """Return a connected wheel instance or None."""
    for dev in hid.enumerate():
        cls = DEVICE_MAP.get((dev['vendor_id'], dev['product_id']))
        if cls:
            wheel = cls()
            if wheel.connect():
                print(f"✔  {cls.__name__} detected "
                      f"({hex(dev['product_id'])})")
                return wheel
    return None

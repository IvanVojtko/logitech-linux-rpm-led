from wheels.wheels import G27
from wheels.wheels import G29
from wheels.wheels import G923xbox
from wheels.wheels import G923ps
from wheels.wheels import GPROxbox
from wheels.wheels import GPROps4
from wheels.wheels import RS50
from wheels.base import BaseWheel
from wheels.hid_backend import enumerate_devices

# Register every VID/PID with its class
DEVICE_MAP: dict[tuple[int, int], type[BaseWheel]] = {}
for cls in (G27, G29, G923xbox, G923ps, GPROxbox, GPROps4, RS50):
    for pid in cls.PRODUCT_IDS:
        DEVICE_MAP[(cls.VENDOR_ID, pid)] = cls


def find_wheel() -> BaseWheel | None:
    """Return a connected wheel instance or None."""
    failures: list[tuple[str, int, Exception | None]] = []
    for dev in enumerate_devices():
        cls = DEVICE_MAP.get((dev['vendor_id'], dev['product_id']))
        if not cls:
            continue
        wheel = cls()
        if wheel.connect(dev['product_id']):
            print(f"✔  {cls.__name__} detected "
                  f"({hex(dev['product_id'])})")
            return wheel
        failures.append((cls.__name__, dev['product_id'], wheel.last_error))

    for name, product_id, error in failures:
        print(f"✖  {name} ({hex(product_id)}) was found but could not be opened: {error}")
    if failures:
        print("   Check that no other application is using the wheel and that you have "
              "hidraw permissions (see the udev rule in the README).")
    return None

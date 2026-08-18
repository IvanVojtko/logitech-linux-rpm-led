from wheels.wheels import G27
from wheels.wheels import G29
from wheels.wheels import G923xbox
from wheels.wheels import G923ps
from wheels.wheels import GPROxbox
from wheels.wheels import GPROps4
from wheels.wheels import RS50
from wheels.base import BaseWheel
from wheels.hid_backend import backend_error, enumerate_devices

# Register every VID/PID with its class
DEVICE_MAP: dict[tuple[int, int], type[BaseWheel]] = {}
for cls in (G27, G29, G923xbox, G923ps, GPROxbox, GPROps4, RS50):
    for pid in cls.PRODUCT_IDS:
        DEVICE_MAP[(cls.VENDOR_ID, pid)] = cls


WheelFailure = tuple[str, int, Exception | None]

PERMISSION_HINT = ("Check that no other application is using the wheel and that you have "
                   "hidraw permissions (see the udev rule in the README).")


def find_wheel_with_failures() -> tuple[BaseWheel | None, list[WheelFailure], str | None]:
    """Return a connected wheel, the wheels seen but unusable, and any backend error.

    The failures matter to the UI: "nothing plugged in" and "plugged in but no
    permission" need different advice, and only the caller can display it. A
    backend error (e.g. the `hid` package can't load its native hidapi library)
    also looks like "nothing plugged in" unless it's reported separately, which
    would otherwise leave the user with no clue why detection silently fails.
    """
    failures: list[WheelFailure] = []
    devices = enumerate_devices()
    for dev in devices:
        cls = DEVICE_MAP.get((dev['vendor_id'], dev['product_id']))
        if not cls:
            continue
        wheel = cls()
        if wheel.connect(dev['product_id']):
            print(f"✔  {cls.__name__} detected "
                  f"({hex(dev['product_id'])})")
            return wheel, [], None
        failures.append((cls.__name__, dev['product_id'], wheel.last_error))

    for name, product_id, error in failures:
        print(f"✖  {name} ({hex(product_id)}) was found but could not be opened: {error}")
    if failures:
        print("   " + PERMISSION_HINT)
        return None, failures, None

    error = backend_error()
    if error:
        print(f"✖  HID backend unavailable: {error}")
    return None, failures, error


def find_wheel() -> BaseWheel | None:
    """Return a connected wheel instance or None."""
    wheel, _failures, _backend_error = find_wheel_with_failures()
    return wheel

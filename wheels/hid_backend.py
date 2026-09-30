from __future__ import annotations

import importlib
from typing import Any


class HidBackendUnavailable(RuntimeError):
    """Raised when the `hid` python package or the hidapi library it wraps cannot be loaded."""


PYTHON_HID_HINT = ("Install the Python 'hid' package: run 'pip install -r requirements.txt' "
                   "in a source checkout, or install python3-hid from your distribution.")
HIDAPI_HINT = ("Install the hidapi library with your package manager (hidapi on Fedora and Arch, "
               "libhidapi-hidraw0 on Debian and Ubuntu, dev-libs/hidapi on Gentoo), then press Rescan.")

_warned_about_legacy_binding = False


def _hid() -> Any:
    try:
        return importlib.import_module("hid")
    except Exception as error:
        # The pip `hid` package is only a ctypes wrapper around the hidapi
        # shared library, and raises ImportError when that library is missing.
        package_missing = isinstance(error, ModuleNotFoundError) and error.name == "hid"
        hint = PYTHON_HID_HINT if package_missing else HIDAPI_HINT
        raise HidBackendUnavailable(f"{error}. {hint}") from error


def is_hid_error(error: Exception) -> bool:
    if isinstance(error, HidBackendUnavailable):
        return True
    try:
        hid = _hid()
    except HidBackendUnavailable:
        return isinstance(error, OSError)
    hid_exception = getattr(hid, "HIDException", None)
    hid_errors = tuple(
        error_type
        for error_type in (hid_exception, OSError)
        if isinstance(error_type, type)
    )
    return isinstance(error, hid_errors)


def enumerate_devices() -> list[dict[str, Any]]:
    """List the HID devices on the system.

    Raises HidBackendUnavailable instead of returning an empty list: without a
    backend no wheel can ever be seen, and reporting that as "nothing plugged
    in" sends the user looking for a hardware problem that does not exist.
    """
    return _hid().enumerate()


def open_device(vendor_id: int, product_id: int) -> Any:
    hid = _hid()
    if hasattr(hid, "Device"):
        return hid.Device(vendor_id, product_id)

    if hasattr(hid, "device"):
        global _warned_about_legacy_binding
        if not _warned_about_legacy_binding:
            print("Warning: Falling back to alternative HID interface, this may not work for your wheel")
            _warned_about_legacy_binding = True
        device = hid.device()
        device.open(vendor_id, product_id)
        return device

    raise RuntimeError("Unsupported Python hid binding")

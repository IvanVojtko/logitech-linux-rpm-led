from __future__ import annotations

import importlib
from typing import Any


class HidBackendUnavailable(RuntimeError):
    """Raised when the `hid` python package cannot be imported."""


_warned_about_legacy_binding = False


def _hid() -> Any:
    try:
        return importlib.import_module("hid")
    except Exception as error:
        raise HidBackendUnavailable(str(error)) from error


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
    try:
        hid = _hid()
    except HidBackendUnavailable:
        return []
    return hid.enumerate()


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

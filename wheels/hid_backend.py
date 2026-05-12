from __future__ import annotations

import importlib
from typing import Any


def _hid() -> Any:
    return importlib.import_module("hid")


def is_hid_error(error: Exception) -> bool:
    hid = _hid()
    hid_exception = getattr(hid, "HIDException", None)
    hid_errors = tuple(
        error_type
        for error_type in (hid_exception, OSError)
        if isinstance(error_type, type)
    )
    return isinstance(error, hid_errors)


def enumerate_devices() -> list[dict[str, Any]]:
    hid = _hid()
    return hid.enumerate()


def open_device(vendor_id: int, product_id: int) -> Any:
    hid = _hid()
    if hasattr(hid, "Device"):
        return hid.Device(vendor_id, product_id)

    if hasattr(hid, "device"):
        device = hid.device()
        device.open(vendor_id, product_id)
        return device

    raise RuntimeError("Unsupported Python hid binding")

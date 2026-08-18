import sys
import types
import unittest
from unittest import mock

from wheels.base import BaseWheel
from wheels.hid_backend import (
    HidBackendUnavailable,
    backend_error,
    enumerate_devices,
    is_hid_error,
    open_device,
)


class TestHidBackend(unittest.TestCase):
    def tearDown(self) -> None:
        sys.modules.pop("hid", None)

    def test_enumerate_devices_returns_empty_list_when_hid_module_missing(self) -> None:
        sys.modules.pop("hid", None)
        with mock.patch(
            "wheels.hid_backend.importlib.import_module",
            side_effect=ModuleNotFoundError("No module named 'hid'"),
        ):
            self.assertEqual(enumerate_devices(), [])

    def test_is_hid_error_true_when_hid_module_missing(self) -> None:
        sys.modules.pop("hid", None)
        with mock.patch(
            "wheels.hid_backend.importlib.import_module",
            side_effect=ModuleNotFoundError("No module named 'hid'"),
        ):
            self.assertTrue(is_hid_error(HidBackendUnavailable("missing")))
            self.assertTrue(is_hid_error(OSError("permission denied")))

    def test_backend_error_reports_reason_when_hid_module_missing(self) -> None:
        sys.modules.pop("hid", None)
        with mock.patch(
            "wheels.hid_backend.importlib.import_module",
            side_effect=ImportError("Unable to load any of the following libraries: ..."),
        ):
            self.assertIn("Unable to load", backend_error())

    def test_backend_error_is_none_when_hid_module_works(self) -> None:
        fake_hid = types.ModuleType("hid")
        sys.modules["hid"] = fake_hid

        self.assertIsNone(backend_error())

    def test_enumerate_devices_delegates_to_hid_module(self) -> None:
        fake_hid = types.ModuleType("hid")
        fake_hid.enumerate = lambda: [{"vendor_id": 0x046d, "product_id": 0xc24f}]
        sys.modules["hid"] = fake_hid

        self.assertEqual(
            enumerate_devices(),
            [{"vendor_id": 0x046d, "product_id": 0xc24f}],
        )

    def test_open_device_supports_python_hid_api(self) -> None:
        fake_hid = types.ModuleType("hid")

        class Device:
            def __init__(self, vendor_id: int, product_id: int) -> None:
                self.vendor_id = vendor_id
                self.product_id = product_id

        fake_hid.Device = Device
        sys.modules["hid"] = fake_hid

        device = open_device(0x046d, 0xc24f)

        self.assertIsInstance(device, Device)
        self.assertEqual(device.vendor_id, 0x046d)
        self.assertEqual(device.product_id, 0xc24f)

    def test_open_device_supports_python_hidapi_api(self) -> None:
        fake_hid = types.ModuleType("hid")

        class Device:
            def open(self, vendor_id: int, product_id: int) -> None:
                self.vendor_id = vendor_id
                self.product_id = product_id

        fake_hid.device = Device
        sys.modules["hid"] = fake_hid

        device = open_device(0x046d, 0xc266)

        self.assertIsInstance(device, Device)
        self.assertEqual(device.vendor_id, 0x046d)
        self.assertEqual(device.product_id, 0xc266)


class TestWheelUsbConnection(unittest.TestCase):
    def tearDown(self) -> None:
        sys.modules.pop("hid", None)

    def test_connect_tries_next_product_id_after_hid_error(self) -> None:
        fake_hid = types.ModuleType("hid")
        fake_hid.HIDException = type("HIDException", (Exception,), {})
        opened_product_ids = []

        class Device:
            def __init__(self, vendor_id: int, product_id: int) -> None:
                opened_product_ids.append(product_id)
                if product_id == 0x0001:
                    raise fake_hid.HIDException("not this one")
                self.vendor_id = vendor_id
                self.product_id = product_id

            def write(self, data: bytes) -> None:
                self.last_write = data

        class TestWheel(BaseWheel):
            PRODUCT_IDS = (0x0001, 0x0002)

            def _led_report(self, bits: int) -> list[int]:
                return [bits]

        fake_hid.Device = Device
        sys.modules["hid"] = fake_hid

        wheel = TestWheel()

        self.assertTrue(wheel.connect())
        self.assertEqual(opened_product_ids, [0x0001, 0x0002])
        self.assertEqual(wheel._dev.product_id, 0x0002)

    def test_connect_returns_false_instead_of_raising_when_hid_module_missing(self) -> None:
        sys.modules.pop("hid", None)

        class TestWheel(BaseWheel):
            PRODUCT_IDS = (0x0001, 0x0002)

            def _led_report(self, bits: int) -> list[int]:
                return [bits]

        with mock.patch(
            "wheels.hid_backend.importlib.import_module",
            side_effect=ModuleNotFoundError("No module named 'hid'"),
        ):
            wheel = TestWheel()
            self.assertFalse(wheel.connect())


if __name__ == "__main__":
    unittest.main()

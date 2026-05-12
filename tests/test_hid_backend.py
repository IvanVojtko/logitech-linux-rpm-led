import sys
import types
import unittest

from wheels.base import BaseWheel
from wheels.hid_backend import enumerate_devices, open_device


class TestHidBackend(unittest.TestCase):
    def tearDown(self) -> None:
        sys.modules.pop("hid", None)

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


if __name__ == "__main__":
    unittest.main()

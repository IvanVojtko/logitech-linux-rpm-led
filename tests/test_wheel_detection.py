import unittest
from unittest import mock

from wheels.base import BaseWheel
from wheels.detect import DEVICE_MAP, find_wheel, find_wheel_with_failures
from wheels.protocols import HIDClassic, HIDpp
from wheels.wheels import G923ps, G923xbox

LOGITECH = 0x046D


class FakeDevice:
    def __init__(self, product_id: int, write_error: Exception | None = None) -> None:
        self.product_id = product_id
        self.writes: list[bytes] = []
        self.closed = False
        self._write_error = write_error

    def write(self, data: bytes) -> None:
        if self._write_error is not None:
            raise self._write_error
        self.writes.append(data)

    def close(self) -> None:
        self.closed = True


class TestDeviceMap(unittest.TestCase):
    def test_g923_playstation_variant_uses_classic_led_protocol(self) -> None:
        # 0xC266 is the PS wheel in PC mode, 0xC267 the same wheel in PS4 mode.
        # Both take the classic 0xF8 0x12 rev light report, not HID++.
        for product_id in (0xC266, 0xC267):
            with self.subTest(product_id=hex(product_id)):
                self.assertIs(DEVICE_MAP[(LOGITECH, product_id)], G923ps)
                self.assertTrue(issubclass(G923ps, HIDClassic))

    def test_g923_xbox_variant_uses_hidpp(self) -> None:
        self.assertIs(DEVICE_MAP[(LOGITECH, 0xC26E)], G923xbox)
        self.assertTrue(issubclass(G923xbox, HIDpp))

    def test_g923_led_report_matches_classic_format(self) -> None:
        self.assertEqual(
            tuple(G923ps()._led_report(0b00111)),
            (0xF8, 0x12, 0b00111, 0x00, 0x00, 0x00, 0x01),
        )


class TestFindWheel(unittest.TestCase):
    def test_only_the_enumerated_product_id_is_opened(self) -> None:
        opened: list[int] = []

        def fake_open(vendor_id: int, product_id: int) -> FakeDevice:
            opened.append(product_id)
            return FakeDevice(product_id)

        with mock.patch(
            "wheels.detect.enumerate_devices",
            return_value=[{"vendor_id": LOGITECH, "product_id": 0xC266}],
        ), mock.patch("wheels.base.open_device", side_effect=fake_open):
            wheel = find_wheel()

        self.assertIsInstance(wheel, G923ps)
        self.assertEqual(opened, [0xC266])

    def test_open_failure_is_reported_instead_of_silently_ignored(self) -> None:
        with mock.patch(
            "wheels.detect.enumerate_devices",
            return_value=[{"vendor_id": LOGITECH, "product_id": 0xC266}],
        ), mock.patch(
            "wheels.base.open_device", side_effect=OSError("Permission denied")
        ), mock.patch("builtins.print") as fake_print:
            self.assertIsNone(find_wheel())

        printed = " ".join(str(call.args[0]) for call in fake_print.call_args_list)
        self.assertIn("0xc266", printed)
        self.assertIn("Permission denied", printed)


class TestFindWheelFailures(unittest.TestCase):
    """The rescan button turns these failures into on-screen advice.

    "Nothing plugged in" and "plugged in but unopenable" need different
    messages, so the reason has to survive the call, not just be printed.
    """

    def test_an_unopenable_wheel_is_returned_as_a_failure(self) -> None:
        with mock.patch(
            "wheels.detect.enumerate_devices",
            return_value=[{"vendor_id": LOGITECH, "product_id": 0xC266}],
        ), mock.patch("wheels.base.open_device", side_effect=OSError("Permission denied")):
            wheel, failures = find_wheel_with_failures()

        self.assertIsNone(wheel)
        self.assertEqual(len(failures), 1)
        name, product_id, error = failures[0]
        self.assertEqual(name, "G923ps")
        self.assertEqual(product_id, 0xC266)
        self.assertIn("Permission denied", str(error))

    def test_no_devices_at_all_reports_no_failures(self) -> None:
        with mock.patch("wheels.detect.enumerate_devices", return_value=[]):
            self.assertEqual(find_wheel_with_failures(), (None, []))

    def test_a_detected_wheel_reports_no_failures(self) -> None:
        with mock.patch(
            "wheels.detect.enumerate_devices",
            return_value=[{"vendor_id": LOGITECH, "product_id": 0xC266}],
        ), mock.patch("wheels.base.open_device", side_effect=lambda v, p: FakeDevice(p)):
            wheel, failures = find_wheel_with_failures()

        self.assertIsInstance(wheel, G923ps)
        self.assertEqual(failures, [])


class TestConnectCleanup(unittest.TestCase):
    def test_device_is_closed_when_post_connect_setup_fails(self) -> None:
        device = FakeDevice(0xC26E, write_error=OSError("wrong protocol"))

        class TestWheel(HIDpp):
            PRODUCT_IDS = [0xC26E]

        with mock.patch("wheels.base.open_device", return_value=device):
            wheel = TestWheel()
            self.assertFalse(wheel.connect())

        self.assertTrue(device.closed)
        self.assertIsNone(wheel._dev)
        self.assertIsInstance(wheel.last_error, OSError)

    def test_close_releases_the_handle_so_a_rescan_can_reopen(self) -> None:
        device = FakeDevice(0xC26E)

        class TestWheel(BaseWheel):
            PRODUCT_IDS = (0xC26E,)

            def _led_report(self, bits: int) -> list[int]:
                return [bits]

        with mock.patch("wheels.base.open_device", return_value=device):
            wheel = TestWheel()
            self.assertTrue(wheel.connect())

        wheel.close()

        self.assertTrue(device.closed)
        self.assertIsNone(wheel._dev)

    def test_connect_without_product_id_still_tries_every_id(self) -> None:
        opened: list[int] = []

        def fake_open(vendor_id: int, product_id: int) -> FakeDevice:
            opened.append(product_id)
            if product_id == 0x0001:
                raise OSError("not connected")
            return FakeDevice(product_id)

        class TestWheel(BaseWheel):
            PRODUCT_IDS = (0x0001, 0x0002)

            def _led_report(self, bits: int) -> list[int]:
                return [bits]

        with mock.patch("wheels.base.open_device", side_effect=fake_open):
            wheel = TestWheel()
            self.assertTrue(wheel.connect())

        self.assertEqual(opened, [0x0001, 0x0002])


if __name__ == "__main__":
    unittest.main()

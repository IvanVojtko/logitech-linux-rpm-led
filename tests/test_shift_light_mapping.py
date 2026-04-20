import unittest

from wheels.base import BaseWheel


class TestShiftLightMapping(unittest.TestCase):
    def tearDown(self) -> None:
        BaseWheel.set_shift_light_thresholds(BaseWheel.DEFAULT_SHIFT_LIGHT_THRESHOLDS)

    def test_leds_stay_off_below_shift_band(self) -> None:
        BaseWheel.set_shift_light_thresholds(BaseWheel.DEFAULT_SHIFT_LIGHT_THRESHOLDS)
        self.assertEqual(BaseWheel._percent_to_bits(67), 0)

    def test_threshold_boundaries(self) -> None:
        BaseWheel.set_shift_light_thresholds(BaseWheel.DEFAULT_SHIFT_LIGHT_THRESHOLDS)
        self.assertEqual(BaseWheel._percent_to_bits(68), 0b00001)
        self.assertEqual(BaseWheel._percent_to_bits(76), 0b00011)
        self.assertEqual(BaseWheel._percent_to_bits(84), 0b00111)
        self.assertEqual(BaseWheel._percent_to_bits(91), 0b01111)
        self.assertEqual(BaseWheel._percent_to_bits(96), 0b11111)

    def test_custom_thresholds_change_activation_points(self) -> None:
        BaseWheel.set_shift_light_thresholds((80, 85, 90, 95, 99))
        self.assertEqual(BaseWheel._percent_to_bits(79), 0)
        self.assertEqual(BaseWheel._percent_to_bits(85), 0b00011)

    def test_unsorted_thresholds_are_normalized(self) -> None:
        normalized = BaseWheel.set_shift_light_thresholds((90, 10, 10, 10, 10))
        self.assertEqual(normalized, (90, 91, 92, 93, 94))

    def test_invalid_threshold_count_resets_defaults(self) -> None:
        normalized = BaseWheel.set_shift_light_thresholds((80, 90, 95))
        self.assertEqual(normalized, tuple(BaseWheel.DEFAULT_SHIFT_LIGHT_THRESHOLDS))


if __name__ == "__main__":
    unittest.main()

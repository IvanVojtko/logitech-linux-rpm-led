from abc import ABC, abstractmethod
from typing import Any, Iterable, Sequence

from wheels.hid_backend import is_hid_error, open_device


class BaseWheel(ABC):
    """Abstract Logitech wheel.

Sub-classes must provide:
VENDOR_ID:  int
PRODUCT_IDS: Iterable[int]
_led_report(bits: int) -> Sequence[int]
    """
    VENDOR_ID: int = 0x046d          # Logitech
    PRODUCT_IDS: Iterable[int] = ()
    DEFAULT_SHIFT_LIGHT_THRESHOLDS: Sequence[int] = (68, 76, 84, 91, 96)
    SHIFT_LIGHT_THRESHOLDS: Sequence[int] = DEFAULT_SHIFT_LIGHT_THRESHOLDS

    def __init__(self) -> None:
        self._dev: Any | None = None
        self._last_bits: int = -1    # cache to avoid spamming


    def connect(self) -> bool:
        for pid in self.PRODUCT_IDS:
            try:
                self._dev = open_device(self.VENDOR_ID, pid)
                self._post_connect_setup()
                return True
            except Exception as error:
                if is_hid_error(error):
                    continue
                raise
        return False

    def leds_rpm(self, percent: float) -> None:
        bits = self._percent_to_bits(percent)
        if bits == self._last_bits or self._dev is None:
            return
        self._last_bits = bits
        self._dev.write(bytes(self._led_report(bits)))

    def _post_connect_setup(self) -> None:
        pass

    @abstractmethod
    def _led_report(self, bits: int) -> Sequence[int]: ...

    # ---------- helpers ----------

    @classmethod
    def set_shift_light_thresholds(cls, thresholds: Sequence[int]) -> tuple[int, ...]:
        expected_count = len(cls.DEFAULT_SHIFT_LIGHT_THRESHOLDS)
        if len(thresholds) != expected_count:
            cls.SHIFT_LIGHT_THRESHOLDS = tuple(cls.DEFAULT_SHIFT_LIGHT_THRESHOLDS)
            return tuple(cls.SHIFT_LIGHT_THRESHOLDS)

        normalized = []
        for index, raw_threshold in enumerate(thresholds):
            low = 0 if index == 0 else normalized[index - 1] + 1
            high = 100 - (expected_count - index - 1)
            threshold = int(raw_threshold)
            normalized.append(max(low, min(threshold, high)))

        cls.SHIFT_LIGHT_THRESHOLDS = tuple(normalized)
        return tuple(cls.SHIFT_LIGHT_THRESHOLDS)

    @staticmethod
    def _percent_to_bits(pct: float) -> int:
        bits = 0
        for index, threshold in enumerate(BaseWheel.SHIFT_LIGHT_THRESHOLDS):
            if pct >= threshold:
                bits |= (1 << index)
        return bits

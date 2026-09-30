import time

BLINK_HALF_PERIOD_SECONDS = 0.1


def _blink_is_lit(now) -> bool:
    """Half of every blink period the lights are on, the other half off.

    Driven by the clock rather than by a packet counter: the telemetry rate
    and the 20 Hz LED write budget in the main loop are both out of our
    hands, so counting packets would make the flash rate unpredictable.
    """
    return int(now / BLINK_HALF_PERIOD_SECONDS) % 2 == 0


def flash_at_limiter(rpm_percent, threshold_percent, now=None):
    """Flash the bar at the limiter instead of holding it solid.

    Returning 0 unconditionally would just switch the lights off and leave
    them off, because nothing alternates between calls; the clock does.
    """
    if rpm_percent < threshold_percent:
        return rpm_percent
    now = time.monotonic() if now is None else now
    return rpm_percent if _blink_is_lit(now) else 0

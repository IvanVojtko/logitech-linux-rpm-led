import struct
import unittest

from games.assetto_corsa_shared_memory import CURR_POS as ACC_CURR_POS
from games.assetto_corsa_shared_memory import MAX_POS as ACC_MAX_POS
from games.assetto_corsa_shared_memory import PHYSICS_TELEMETRY as ACC_PHYSICS_TELEMETRY
from games.assetto_corsa_shared_memory import STATIC_TELEMETRY as ACC_STATIC_TELEMETRY
from games.assetto_corsa_shared_memory import AssettoCorsaSharedMemory
from games.dirt_rally_2_0 import CURR_POS as DIRT_CURR_POS
from games.dirt_rally_2_0 import MAX_POS as DIRT_MAX_POS
from games.dirt_rally_2_0 import DirtRally2
from games.assetto_corsa import CURRENT_RPM_POS as AC_CURRENT_RPM_POS
from games.assetto_corsa import PACKET_IDENTIFIER as AC_PACKET_IDENTIFIER
from games.assetto_corsa import PACKET_SIZE_POS as AC_PACKET_SIZE_POS
from games.assetto_corsa import AssettoCorsa
from games.f1 import CAR_TELEMETRY_ID as F1_TELEMETRY_ID
from games.f1 import F12019, F12020, F12022, F12023
from games.forza_horizon import ForzaHorizon5, ForzaHorizon6
from games.truck_simulator import PACKET_MAGIC as SCS_TS_PACKET_MAGIC
from games.truck_simulator import PACKET_STRUCT as SCS_TS_PACKET_STRUCT
from games.truck_simulator import PACKET_VERSION as SCS_TS_PACKET_VERSION
from games.truck_simulator import TruckSimulator
from games.rev_limiter import BLINK_HALF_PERIOD_SECONDS
from games.wreckfest_2 import BLINK_THRESHOLD_PERCENT as WRECKFEST_2_BLINK_THRESHOLD
from games.wreckfest_2 import CURR_POS as WRECKFEST_2_CURR_POS
from games.wreckfest_2 import MAX_POS as WRECKFEST_2_MAX_POS
from games.wreckfest_2 import Wreckfest2


def _field_count(fmt: str) -> int:
    return len(struct.unpack(fmt, bytes(struct.calcsize(fmt))))


def _build_f1_packet(
    header_fmt: str,
    car_fmt: str,
    packet_id_pos: int,
    player_car_index_pos: int,
    player_car_index: int,
    rev_percents: list[int],
) -> bytes:
    header_values = [0] * _field_count(header_fmt)
    header_values[packet_id_pos] = F1_TELEMETRY_ID
    header_values[player_car_index_pos] = player_car_index
    header = struct.pack(header_fmt, *header_values)

    car_values_count = _field_count(car_fmt)
    cars = []
    for rev_percent in rev_percents:
        car_values = [0] * car_values_count
        car_values[8] = rev_percent
        cars.append(struct.pack(car_fmt, *car_values))
    return header + b"".join(cars)


def _build_forza_packet(max_rpm: float, current_rpm: float) -> bytes:
    packet = bytearray(20)
    packet[8:12] = struct.pack("<f", max_rpm)
    packet[16:20] = struct.pack("<f", current_rpm)
    return bytes(packet)


class TestForzaParser(unittest.TestCase):
    def test_short_packet_returns_previous_percent(self) -> None:
        game = ForzaHorizon5()
        self.assertEqual(game.get_rpm_percent(b"\x00" * 8, 37), 37)

    def test_valid_packet_computes_percent(self) -> None:
        game = ForzaHorizon5()
        self.assertEqual(game.get_rpm_percent(_build_forza_packet(9000.0, 4500.0), 7), 50)

    def test_engine_off_returns_zero(self) -> None:
        game = ForzaHorizon5()
        self.assertEqual(game.get_rpm_percent(_build_forza_packet(9000.0, 0.0), 73), 0)

    def test_forza_horizon_6_uses_same_parser(self) -> None:
        game = ForzaHorizon6()
        self.assertEqual(game.get_rpm_percent(_build_forza_packet(8000.0, 6000.0), 7), 75)


class TestDirtParser(unittest.TestCase):
    def test_short_packet_returns_previous_percent(self) -> None:
        game = DirtRally2()
        self.assertEqual(game.get_rpm_percent(b"\x00" * 10, 37), 37)

    def test_valid_packet_computes_percent(self) -> None:
        game = DirtRally2()
        values = [0.0] * 66
        values[DIRT_MAX_POS] = 8000.0
        values[DIRT_CURR_POS] = 4000.0
        packet = struct.pack("<66f", *values)
        self.assertEqual(game.get_rpm_percent(packet, 0), 50)


class TestAssettoCorsaParser(unittest.TestCase):
    def test_valid_packet_computes_percent(self) -> None:
        game = AssettoCorsa(max_rpm=9000)
        packet = bytearray(128)
        packet[0] = AC_PACKET_IDENTIFIER
        packet[AC_PACKET_SIZE_POS:AC_PACKET_SIZE_POS + 4] = struct.pack("<i", len(packet))
        packet[AC_CURRENT_RPM_POS:AC_CURRENT_RPM_POS + 4] = struct.pack("<f", 4500.0)
        self.assertEqual(game.get_rpm_percent(bytes(packet), 7), 50)

    def test_invalid_packet_returns_previous_percent(self) -> None:
        game = AssettoCorsa(max_rpm=9000)
        packet = bytearray(128)
        packet[0] = ord("z")
        packet[AC_PACKET_SIZE_POS:AC_PACKET_SIZE_POS + 4] = struct.pack("<i", len(packet))
        packet[AC_CURRENT_RPM_POS:AC_CURRENT_RPM_POS + 4] = struct.pack("<f", 4500.0)
        self.assertEqual(game.get_rpm_percent(bytes(packet), 41), 41)

    def test_zero_rpm_returns_zero(self) -> None:
        game = AssettoCorsa(max_rpm=9000)
        packet = bytearray(128)
        packet[0] = AC_PACKET_IDENTIFIER
        packet[AC_PACKET_SIZE_POS:AC_PACKET_SIZE_POS + 4] = struct.pack("<i", len(packet))
        packet[AC_CURRENT_RPM_POS:AC_CURRENT_RPM_POS + 4] = struct.pack("<f", 0.0)
        self.assertEqual(game.get_rpm_percent(bytes(packet), 73), 0)


def _build_acc_data(current_rpm: int, max_rpm: int) -> list[bytes]:
    physics = list(ACC_PHYSICS_TELEMETRY.unpack(bytes(ACC_PHYSICS_TELEMETRY.size)))
    physics[ACC_CURR_POS] = current_rpm
    static = list(ACC_STATIC_TELEMETRY.unpack(bytes(ACC_STATIC_TELEMETRY.size)))
    static[ACC_MAX_POS] = max_rpm
    return [ACC_PHYSICS_TELEMETRY.pack(*physics), ACC_STATIC_TELEMETRY.pack(*static)]


class TestAssettoCorsaSharedMemoryParser(unittest.TestCase):
    def test_reads_max_rpm_from_static_data(self) -> None:
        game = AssettoCorsaSharedMemory()
        self.assertEqual(game.get_rpm_percent(_build_acc_data(4500, 9000), 7), 50)

    def test_user_max_rpm_overrides_static_data(self) -> None:
        game = AssettoCorsaSharedMemory(max_rpm=6000)
        self.assertEqual(game.get_rpm_percent(_build_acc_data(4500, 9000), 7), 75)

    def test_below_the_limiter_reports_the_real_percent(self) -> None:
        # The flash used to count ticks in prev_value, so climbing into the
        # 90s from a low reading reported 1% and 2% before the real value.
        game = AssettoCorsaSharedMemory()
        self.assertEqual(game.get_rpm_percent(_build_acc_data(8190, 9000), 0), 91)


class TestScsTruckSimulatorParser(unittest.TestCase):
    def test_valid_packet_computes_percent(self) -> None:
        game = TruckSimulator()
        packet = SCS_TS_PACKET_STRUCT.pack(SCS_TS_PACKET_MAGIC, SCS_TS_PACKET_VERSION, 1, 0, 1050.0, 2100.0)
        self.assertEqual(game.get_rpm_percent(packet, 7), 50)

    def test_paused_packet_returns_zero(self) -> None:
        game = TruckSimulator()
        packet = SCS_TS_PACKET_STRUCT.pack(SCS_TS_PACKET_MAGIC, SCS_TS_PACKET_VERSION, 0, 0, 1050.0, 2100.0)
        self.assertEqual(game.get_rpm_percent(packet, 73), 0)

    def test_invalid_packet_returns_previous_percent(self) -> None:
        game = TruckSimulator()
        packet = SCS_TS_PACKET_STRUCT.pack(b"BAD!", SCS_TS_PACKET_VERSION, 1, 0, 1050.0, 2100.0)
        self.assertEqual(game.get_rpm_percent(packet, 41), 41)

    def test_missing_max_rpm_returns_previous_percent(self) -> None:
        game = TruckSimulator()
        packet = SCS_TS_PACKET_STRUCT.pack(SCS_TS_PACKET_MAGIC, SCS_TS_PACKET_VERSION, 1, 0, 1050.0, 0.0)
        self.assertEqual(game.get_rpm_percent(packet, 23), 23)


class TestF1PlayerCarSelection(unittest.TestCase):
    def test_uses_player_car_index_for_all_f1_versions(self) -> None:
        cases = [
            (
                "F1 2019",
                F12019(),
                "<HBBBBQfIB",
                "<HfffBbHBB4H4H4HH4f4B",
                F12019.PACKET_ID_POS,
                F12019.PLAYER_CAR_INDEX_POS,
            ),
            (
                "F1 2020",
                F12020(),
                "<HBBBBQfIBB",
                "<HfffBbHBB4H4B4BH4f4B",
                F12020.PACKET_ID_POS,
                F12020.PLAYER_CAR_INDEX_POS,
            ),
            (
                "F1 2022",
                F12022(),
                "<HBBBBQfIBB",
                "<HfffBbHBBH4H4B4BH4f4B",
                F12022.PACKET_ID_POS,
                F12022.PLAYER_CAR_INDEX_POS,
            ),
            (
                "F1 2023",
                F12023(),
                "<HBBBBBQfIIBB",
                "<HfffBbHBBH4H4B4BH4f4B",
                F12023.PACKET_ID_POS,
                F12023.PLAYER_CAR_INDEX_POS,
            ),
        ]

        for name, game, header_fmt, car_fmt, packet_pos, player_pos in cases:
            with self.subTest(name=name):
                packet = _build_f1_packet(
                    header_fmt=header_fmt,
                    car_fmt=car_fmt,
                    packet_id_pos=packet_pos,
                    player_car_index_pos=player_pos,
                    player_car_index=1,
                    rev_percents=[12, 87],
                )
                self.assertEqual(game.get_rpm_percent(packet, 5), 87)

    def test_invalid_player_index_returns_previous_percent(self) -> None:
        packet = _build_f1_packet(
            header_fmt="<HBBBBQfIB",
            car_fmt="<HfffBbHBB4H4H4HH4f4B",
            packet_id_pos=F12019.PACKET_ID_POS,
            player_car_index_pos=F12019.PLAYER_CAR_INDEX_POS,
            player_car_index=22,
            rev_percents=[50, 60],
        )
        self.assertEqual(F12019().get_rpm_percent(packet, 33), 33)


class TestWreckfest2Parser(unittest.TestCase):
    def test_short_packet_returns_previous_percent(self) -> None:
        game = Wreckfest2()
        self.assertEqual(game.get_rpm_percent(b"\x00" * WRECKFEST_2_MAX_POS, 37), 37)

    def test_truncated_packet_under_five_bytes_does_not_raise(self) -> None:
        game = Wreckfest2()
        for size in range(0, 5):
            with self.subTest(size=size):
                self.assertEqual(game.get_rpm_percent(b"\x00" * size, 37), 37)

    def test_invalid_signed_packet_returns_previous_percent(self) -> None:
        game = Wreckfest2()
        values= [b'\x00'] * 500
        # Set valid signature
        values[0:4] = (1111111111).to_bytes(4, byteorder='little')
        # Set "main" packet flag
        values[4:5] = b'\x00'
        # Set current RPM to 50% of max RPM
        values[WRECKFEST_2_CURR_POS:WRECKFEST_2_CURR_POS + 4] = (4000).to_bytes(4, byteorder='little', signed=True)
        values[WRECKFEST_2_MAX_POS:WRECKFEST_2_MAX_POS + 4] = (8000).to_bytes(4, byteorder='little', signed=True)
        # Check using previous RPM and not calculated one
        self.assertEqual(game.get_rpm_percent(values, 37), 37)

    def test_not_main_packet_returns_previous_percent(self) -> None:
        game = Wreckfest2()
        values= [b'\x00'] * 500
        # Set valid signature
        values[0:4] = (1869769584).to_bytes(4, byteorder='little')
        # Set ignored packet flag
        values[4:5] = b'\x01'
        # Check using previous RPM
        self.assertEqual(game.get_rpm_percent(values, 37), 37)

    def test_valid_packet_computes_percent(self) -> None:
        game = Wreckfest2()
        values= [b'\x00'] * 500
        # Set valid signature
        values[0:4] = (1869769584).to_bytes(4, byteorder='little')
        # Set "main" packet flag
        values[4:5] = b'\x00'
        # Set current RPM to 50% of max RPM
        values[WRECKFEST_2_CURR_POS:WRECKFEST_2_CURR_POS + 4] = (4000).to_bytes(4, byteorder='little', signed=True)
        values[WRECKFEST_2_MAX_POS:WRECKFEST_2_MAX_POS + 4] = (8000).to_bytes(4, byteorder='little', signed=True)
        # Check using correct calculated RPM
        self.assertEqual(game.get_rpm_percent(values, 10), 50)


class TestF1PacketLayouts(unittest.TestCase):
    """Anchor each struct against the packet size the game actually sends.

    A car struct declared with the wrong field widths still round-trips through
    a test that builds its packets with that same struct, so the layouts are
    checked against the documented grid size instead. F1 2022 shipped with
    uint16 tyre temperature arrays and yielded 19 cars instead of 22.
    """

    def test_car_struct_size_yields_the_documented_grid(self) -> None:
        cases = [
            ("F1 2019", F12019, 20),
            ("F1 2020", F12020, 22),
            ("F1 2022", F12022, 22),
            ("F1 2023", F12023, 22),
        ]
        for name, game_class, expected_cars in cases:
            with self.subTest(name=name):
                car_size = game_class.CAR_TELEMETRY.size
                payload = game_class.BUFFER_SIZE - game_class.PACKET_HEADER.size
                self.assertEqual(payload // car_size, expected_cars)
                # Whatever is left over are the few trailing fields after the
                # car array, never a whole car's worth of slack.
                self.assertLess(payload % car_size, car_size)


class TestWreckfest2Blink(unittest.TestCase):
    def test_limiter_alternates_between_lit_and_dark(self) -> None:
        game = Wreckfest2()
        game.rpm, game.rpmMax = 7960, 8000  # 99.5%, on the limiter

        half = BLINK_HALF_PERIOD_SECONDS
        seen = [game.calc_rpm_percent(now=half * tick) for tick in range(6)]

        self.assertTrue(any(value == 0 for value in seen), seen)
        self.assertTrue(any(value >= WRECKFEST_2_BLINK_THRESHOLD for value in seen), seen)

    def test_below_the_limiter_reports_the_real_percent(self) -> None:
        game = Wreckfest2()
        game.rpm, game.rpmMax = 7000, 8000  # 87.5%

        half = BLINK_HALF_PERIOD_SECONDS
        for tick in range(6):
            with self.subTest(tick=tick):
                self.assertAlmostEqual(game.calc_rpm_percent(now=half * tick), 87.5)

    def test_non_positive_max_rpm_reports_zero(self) -> None:
        game = Wreckfest2()
        game.rpm, game.rpmMax = 7000, -1
        self.assertEqual(game.calc_rpm_percent(now=0.0), 0)


if __name__ == "__main__":
    unittest.main()

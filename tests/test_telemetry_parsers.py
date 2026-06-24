import struct
import unittest

from games.dirt_rally_2_0 import CURR_POS as DIRT_CURR_POS
from games.dirt_rally_2_0 import MAX_POS as DIRT_MAX_POS
from games.dirt_rally_2_0 import DirtRally2
from games.assetto_corsa import CURRENT_RPM_POS as AC_CURRENT_RPM_POS
from games.assetto_corsa import PACKET_IDENTIFIER as AC_PACKET_IDENTIFIER
from games.assetto_corsa import PACKET_SIZE_POS as AC_PACKET_SIZE_POS
from games.assetto_corsa import AssettoCorsa
from games.f12019 import CAR_TELEMETRY_ID as F12019_TELEMETRY_ID
from games.f12019 import PACKET_ID_POS as F12019_PACKET_ID_POS
from games.f12019 import PLAYER_CAR_INDEX_POS as F12019_PLAYER_CAR_INDEX_POS
from games.f12019 import F12019
from games.f12020 import PACKET_ID_POS as F12020_PACKET_ID_POS
from games.f12020 import PLAYER_CAR_INDEX_POS as F12020_PLAYER_CAR_INDEX_POS
from games.f12020 import F12020
from games.f12022 import PACKET_ID_POS as F12022_PACKET_ID_POS
from games.f12022 import PLAYER_CAR_INDEX_POS as F12022_PLAYER_CAR_INDEX_POS
from games.f12022 import F12022
from games.f12023 import PACKET_ID_POS as F12023_PACKET_ID_POS
from games.f12023 import PLAYER_CAR_INDEX_POS as F12023_PLAYER_CAR_INDEX_POS
from games.f12023 import F12023
from games.forza_horizon import ForzaHorizon5, ForzaHorizon6
from games.euro_truck_simulator_2 import PACKET_MAGIC as ETS2_PACKET_MAGIC
from games.euro_truck_simulator_2 import PACKET_STRUCT as ETS2_PACKET_STRUCT
from games.euro_truck_simulator_2 import PACKET_VERSION as ETS2_PACKET_VERSION
from games.euro_truck_simulator_2 import EuroTruckSimulator2


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
    header_values[packet_id_pos] = F12019_TELEMETRY_ID
    header_values[player_car_index_pos] = player_car_index
    header = struct.pack(header_fmt, *header_values)

    car_values_count = _field_count(car_fmt)
    cars = []
    for rev_percent in rev_percents:
        car_values = [0] * car_values_count
        car_values[8] = rev_percent
        cars.append(struct.pack(car_fmt, *car_values))
    return header + b"".join(cars)


class TestForzaParser(unittest.TestCase):
    def test_parse_rpm_handles_short_packet(self) -> None:
        game = ForzaHorizon5()
        max_rpm, curr_rpm = game.parse_rpm(b"\x00" * 8)
        self.assertEqual(max_rpm, 0.0)
        self.assertEqual(curr_rpm, 0.0)

    def test_parse_rpm_reads_values(self) -> None:
        game = ForzaHorizon5()
        packet = bytearray(20)
        packet[8:12] = struct.pack("<f", 9000.0)
        packet[16:20] = struct.pack("<f", 4500.0)
        max_rpm, curr_rpm = game.parse_rpm(bytes(packet))
        self.assertAlmostEqual(max_rpm, 9000.0)
        self.assertAlmostEqual(curr_rpm, 4500.0)

    def test_forza_horizon_6_uses_same_parser(self) -> None:
        game = ForzaHorizon6()
        packet = bytearray(20)
        packet[8:12] = struct.pack("<f", 8000.0)
        packet[16:20] = struct.pack("<f", 6000.0)
        max_rpm, curr_rpm = game.parse_rpm(bytes(packet))
        self.assertAlmostEqual(max_rpm, 8000.0)
        self.assertAlmostEqual(curr_rpm, 6000.0)


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


class TestEuroTruckSimulator2Parser(unittest.TestCase):
    def test_valid_packet_computes_percent(self) -> None:
        game = EuroTruckSimulator2()
        packet = ETS2_PACKET_STRUCT.pack(ETS2_PACKET_MAGIC, ETS2_PACKET_VERSION, 1, 0, 1050.0, 2100.0)
        self.assertEqual(game.get_rpm_percent(packet, 7), 50)

    def test_paused_packet_returns_zero(self) -> None:
        game = EuroTruckSimulator2()
        packet = ETS2_PACKET_STRUCT.pack(ETS2_PACKET_MAGIC, ETS2_PACKET_VERSION, 0, 0, 1050.0, 2100.0)
        self.assertEqual(game.get_rpm_percent(packet, 73), 0)

    def test_invalid_packet_returns_previous_percent(self) -> None:
        game = EuroTruckSimulator2()
        packet = ETS2_PACKET_STRUCT.pack(b"BAD!", ETS2_PACKET_VERSION, 1, 0, 1050.0, 2100.0)
        self.assertEqual(game.get_rpm_percent(packet, 41), 41)

    def test_missing_max_rpm_returns_previous_percent(self) -> None:
        game = EuroTruckSimulator2()
        packet = ETS2_PACKET_STRUCT.pack(ETS2_PACKET_MAGIC, ETS2_PACKET_VERSION, 1, 0, 1050.0, 0.0)
        self.assertEqual(game.get_rpm_percent(packet, 23), 23)


class TestF1PlayerCarSelection(unittest.TestCase):
    def test_uses_player_car_index_for_all_f1_versions(self) -> None:
        cases = [
            (
                "F1 2019",
                F12019(),
                "<HBBBBQfIB",
                "<HfffBbHBB4H4H4HH4f4B",
                F12019_PACKET_ID_POS,
                F12019_PLAYER_CAR_INDEX_POS,
            ),
            (
                "F1 2020",
                F12020(),
                "<HBBBBQfIBB",
                "<HfffBbHBB4H4B4BH4f4B",
                F12020_PACKET_ID_POS,
                F12020_PLAYER_CAR_INDEX_POS,
            ),
            (
                "F1 2022",
                F12022(),
                "<HBBBBQfIBB",
                "<HfffBbHBBH4H4H4HH4f4B",
                F12022_PACKET_ID_POS,
                F12022_PLAYER_CAR_INDEX_POS,
            ),
            (
                "F1 2023",
                F12023(),
                "<HBBBBBQfIIBB",
                "<HfffBbHBBH4H4B4BH4f4B",
                F12023_PACKET_ID_POS,
                F12023_PLAYER_CAR_INDEX_POS,
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
            packet_id_pos=F12019_PACKET_ID_POS,
            player_car_index_pos=F12019_PLAYER_CAR_INDEX_POS,
            player_car_index=22,
            rev_percents=[50, 60],
        )
        self.assertEqual(F12019().get_rpm_percent(packet, 33), 33)


if __name__ == "__main__":
    unittest.main()

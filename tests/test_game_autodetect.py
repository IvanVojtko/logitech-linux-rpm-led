import unittest

from games.autodetect import detect_game_from_processes


class TestGameAutoDetect(unittest.TestCase):
    def test_detect_assetto_corsa_by_steam_app_id(self) -> None:
        processes = [
            {"name": "wine64", "cmdline": "wine64-preloader", "steam_app_id": ""},
            {"name": "wineserver", "cmdline": "", "steam_app_id": "244210"},
        ]
        self.assertEqual(detect_game_from_processes(processes), "assetto_corsa")

    def test_should_not_detect_acc_when_name_in_other_process(self) -> None:
        processes = [
            {"name": "steam", "cmdline": "steam", "steam_app_id": ""},
            {"name": "discord", "cmdline": "--enable-crash-reporter=9022b9dc-ac2--1-8f45-8f69e14bb8d5", "steam_app_id": "000000"},
            {"name": "firefox-bin", "cmdline": "-initialChannelId {de789fbd--ac2-45bb-8b6d-36393222b64a}", "steam_app_id": "000000"},
            {"name": "test_process1", "cmdline": "-ac2", "steam_app_id": "000000"},
            {"name": "test_process2", "cmdline": "_ac2", "steam_app_id": "000000"},
            {"name": "test_process1", "cmdline": "ac2-", "steam_app_id": "000000"},
            {"name": "test_process2", "cmdline": "ac2_", "steam_app_id": "000000"},
            {"name": "test_process3", "cmdline": "ac2=true", "steam_app_id": "000000"},
        ]
        self.assertIsNone(detect_game_from_processes(processes))

    def test_should_detect_acc_when_token_assigned(self) -> None:
        processes = [
            {"name": "steam", "cmdline": "steam", "steam_app_id": ""},
            {"name": "test_process", "cmdline": " --exe=ac2 ", "steam_app_id": "000000"},
        ]
        self.assertEqual(detect_game_from_processes(processes), "assetto_corsa_competizione")

    def test_should_detect_acc_when_token_as_word(self) -> None:
        processes = [
            {"name": "steam", "cmdline": "steam", "steam_app_id": ""},
            {"name": "start_process", "cmdline": "--exe ac2", "steam_app_id": "000000"},
        ]
        self.assertEqual(detect_game_from_processes(processes), "assetto_corsa_competizione")

    def test_detect_f1_23_by_process_token(self) -> None:
        processes = [
            {
                "name": "wine64-preloader",
                "cmdline": "/path/to/F1_23.exe",
                "steam_app_id": "",
            }
        ]
        self.assertEqual(detect_game_from_processes(processes), "f1_2023")

    def test_detects_dirt_rally_2_by_name(self) -> None:
        processes = [
            {"name": "steam", "cmdline": "steam", "steam_app_id": ""},
            {"name": "dirt rally 2.0", "cmdline": "", "steam_app_id": "000000"},
        ]
        self.assertEqual(detect_game_from_processes(processes), "dirt_rally_2_0")

    def test_does_not_detect_dirt_rally_2_by_name_when_point_replaced_by_X(self) -> None:
        processes = [
            {"name": "steam", "cmdline": "steam", "steam_app_id": ""},
            {"name": "dirt rally 2X0", "cmdline": "", "steam_app_id": "000000"},
        ]
        self.assertIsNone(detect_game_from_processes(processes))

    def test_detects_ets2_by_steam_app_id(self) -> None:
        processes = [
            {"name": "steam", "cmdline": "steam", "steam_app_id": ""},
            {"name": "UNKNOWN NAME", "cmdline": "", "steam_app_id": "227300"},
        ]
        self.assertEqual(detect_game_from_processes(processes), "truck_simulator")

    def test_detects_ets2_by_name(self) -> None:
        processes = [
            {"name": "steam", "cmdline": "steam", "steam_app_id": ""},
            {"name": "euro truck simulator 2", "cmdline": "", "steam_app_id": "000000"},
        ]
        self.assertEqual(detect_game_from_processes(processes), "truck_simulator")

    def test_detects_ats_by_steam_app_id(self) -> None:
        processes = [
            {"name": "steam", "cmdline": "steam", "steam_app_id": ""},
            {"name": "wineserver", "cmdline": "", "steam_app_id": "270880"},
        ]
        self.assertEqual(detect_game_from_processes(processes), "truck_simulator")

    def test_detects_ats_by_name(self) -> None:
        processes = [
            {"name": "steam", "cmdline": "steam", "steam_app_id": ""},
            {"name": "american truck simulator", "cmdline": "", "steam_app_id": "000000"},
        ]
        self.assertEqual(detect_game_from_processes(processes), "truck_simulator")

    def test_detects_forza_horizon_6_by_steam_app_id(self) -> None:
        processes = [
            {"name": "wineserver", "cmdline": "", "steam_app_id": "2483190"},
        ]
        self.assertEqual(detect_game_from_processes(processes), "forza_horizon_6")

    def test_detects_forza_horizon_6_by_process_token(self) -> None:
        processes = [
            {
                "name": "wine64-preloader",
                "cmdline": "/path/to/forzahorizon6.exe",
                "steam_app_id": "",
            }
        ]
        self.assertEqual(detect_game_from_processes(processes), "forza_horizon_6")

    def test_detects_forza_horizon_6_by_name(self) -> None:
        processes = [
            {"name": "forzahorizon6.exe", "cmdline": "", "steam_app_id": "000000000"},
        ]
        self.assertEqual(detect_game_from_processes(processes), "forza_horizon_6")

    def test_detect_project_cars_by_steam_app_id(self) -> None:
        processes = [
            {"name": "wine64", "cmdline": "wine64-preloader", "steam_app_id": ""},
            {"name": "wineserver", "cmdline": "", "steam_app_id": "234630"},
        ]
        self.assertEqual(detect_game_from_processes(processes), "ams_2")

    def test_detect_project_cars_by_name(self) -> None:
        processes = [
            {"name": "wine64", "cmdline": "wine64-preloader", "steam_app_id": ""},
            {"name": "pcars64.exe", "cmdline": "", "steam_app_id": "00000"},
        ]
        self.assertEqual(detect_game_from_processes(processes), "ams_2")

    def test_detects_wreckfest_2_by_steam_app_id(self) -> None:
        processes = [
            {"name": "steam", "cmdline": "steam", "steam_app_id": ""},
            {"name": "wineserver", "cmdline": "", "steam_app_id": "1203190"},
        ]
        self.assertEqual(detect_game_from_processes(processes), "wreckfest_2")

    def test_detects_wreckfest_2_by_name(self) -> None:
        processes = [
            {"name": "steam", "cmdline": "steam", "steam_app_id": ""},
            {"name": "Wreckfest2.exe", "cmdline": "", "steam_app_id": "000000"},
        ]
        self.assertEqual(detect_game_from_processes(processes), "wreckfest_2")

    def test_returns_none_when_no_match(self) -> None:
        processes = [
            {"name": "steam", "cmdline": "steamwebhelper", "steam_app_id": ""},
            {"name": "python", "cmdline": "main.py", "steam_app_id": ""},
        ]
        self.assertIsNone(detect_game_from_processes(processes))


if __name__ == "__main__":
    unittest.main()

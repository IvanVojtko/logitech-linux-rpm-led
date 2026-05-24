import unittest

from games.autodetect import detect_game_from_processes


class TestGameAutoDetect(unittest.TestCase):
    def test_detects_by_steam_app_id(self) -> None:
        processes = [
            {"name": "wine64", "cmdline": "wine64-preloader", "steam_app_id": ""},
            {"name": "wineserver", "cmdline": "", "steam_app_id": "244210"},
        ]
        self.assertEqual(detect_game_from_processes(processes), "assetto_corsa")

    def test_detects_by_process_token(self) -> None:
        processes = [
            {
                "name": "wine64-preloader",
                "cmdline": "/path/to/F1_23.exe",
                "steam_app_id": "",
            }
        ]
        self.assertEqual(detect_game_from_processes(processes), "f1_2023")

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

    def test_returns_none_when_no_match(self) -> None:
        processes = [
            {"name": "steam", "cmdline": "steamwebhelper", "steam_app_id": ""},
            {"name": "python", "cmdline": "main.py", "steam_app_id": ""},
        ]
        self.assertIsNone(detect_game_from_processes(processes))


if __name__ == "__main__":
    unittest.main()

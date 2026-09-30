import unittest
from pathlib import Path

from games.autodetect import GAME_SIGNATURES
from games.registry import GAME_INDEX_BY_KEY, GAMES

ICONS_DIR = Path(__file__).resolve().parents[1] / "icons"


class TestGameRegistry(unittest.TestCase):
    def test_keys_are_unique(self) -> None:
        keys = [game.key for game in GAMES]
        self.assertEqual(len(keys), len(set(keys)))

    def test_index_by_key_follows_the_list_order(self) -> None:
        for index, game in enumerate(GAMES):
            with self.subTest(game=game.key):
                self.assertEqual(GAME_INDEX_BY_KEY[game.key], index)

    def test_every_auto_detected_game_can_be_selected(self) -> None:
        detected_keys = {signature["key"] for signature in GAME_SIGNATURES}
        self.assertEqual(detected_keys - set(GAME_INDEX_BY_KEY), set())

    def test_every_icon_exists(self) -> None:
        for game in GAMES:
            with self.subTest(game=game.key):
                self.assertTrue((ICONS_DIR / game.icon).is_file())

    def test_games_asking_for_max_rpm_have_a_label(self) -> None:
        for game in GAMES:
            if game.needs_max_rpm:
                with self.subTest(game=game.key):
                    self.assertTrue(game.max_rpm_label)

    def test_every_game_provides_the_telemetry_interface(self) -> None:
        for game in GAMES:
            with self.subTest(game=game.key):
                source = game.create(max_rpm=game.default_max_rpm) if game.needs_max_rpm else game.create()
                for method in ("connect", "read_data", "get_rpm_percent"):
                    self.assertTrue(callable(getattr(source, method, None)), method)


if __name__ == "__main__":
    unittest.main()

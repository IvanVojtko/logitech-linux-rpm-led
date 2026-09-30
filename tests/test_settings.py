import unittest

from games.registry import GAMES

try:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")

    import main

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False


@unittest.skipUnless(GTK_AVAILABLE, "GTK 4 / libadwaita bindings are not available")
class TestLastSelectedGameSetting(unittest.TestCase):
    """The remembered game is saved by key, so adding a game cannot shift it."""

    def _parse(self, raw_value):
        return main.WheelRPMWindow._parse_last_selected_game(raw_value)

    def test_game_key_is_kept(self) -> None:
        self.assertEqual(self._parse("f1_2023"), "f1_2023")

    def test_legacy_position_is_read_against_the_current_list(self) -> None:
        self.assertEqual(self._parse("10"), GAMES[10].key)

    def test_unknown_value_falls_back_to_the_default(self) -> None:
        for raw_value in ("", "not_a_game", str(len(GAMES)), "-1"):
            with self.subTest(raw_value=raw_value):
                self.assertEqual(self._parse(raw_value), main.DEFAULT_LAST_SELECTED_GAME)


if __name__ == "__main__":
    unittest.main()

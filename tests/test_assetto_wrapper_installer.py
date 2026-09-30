import tempfile
import unittest
from pathlib import Path
from unittest import mock

from installers.assetto_wrapper_installer import (
    ACC_APP_ID,
    ACC_DIR_NAME,
    ACC_EXE_NAME,
    WRAPPER_DIR_NAME,
    WRAPPER_FILE_NAME,
    WRAPPER_INSTALLED,
    WRAPPER_MARKER,
    WRAPPER_MISSING,
    acc_wrapper_status,
    install_acc_wrapper,
    is_wrapper_executable,
)

ROOT = Path(__file__).resolve().parents[1]
WRAPPER_BYTES = b"MZ wrapper build " + WRAPPER_MARKER + b"%s"
GAME_BYTES = b"MZ the real game"


class TestAssettoWrapperInstaller(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        base = Path(temp_dir.name)

        self.steam_root = base / "Steam"
        steamapps = self.steam_root / "steamapps"
        steamapps.mkdir(parents=True)
        (steamapps / f"appmanifest_{ACC_APP_ID}.acf").write_text("", encoding="utf-8")
        game_dir = steamapps / "common" / ACC_DIR_NAME
        game_dir.mkdir(parents=True)
        self.exe = game_dir / ACC_EXE_NAME
        self.original_exe = game_dir / ("_" + ACC_EXE_NAME)

        self.app_dir = base / "app"
        self.wrapper = self.app_dir / WRAPPER_DIR_NAME / WRAPPER_FILE_NAME
        self.wrapper.parent.mkdir(parents=True)
        self.wrapper.write_bytes(WRAPPER_BYTES)

    def _install(self):
        return install_acc_wrapper(steam_roots=[self.steam_root], app_dir=self.app_dir)

    def _status(self):
        state, _installed_paths = acc_wrapper_status(steam_roots=[self.steam_root])
        return state

    def test_first_install_moves_the_game_aside(self) -> None:
        self.exe.write_bytes(GAME_BYTES)
        self.assertEqual(self._status(), WRAPPER_MISSING)

        self.assertEqual(self._install(), [self.exe])

        self.assertEqual(self.original_exe.read_bytes(), GAME_BYTES)
        self.assertEqual(self.exe.read_bytes(), WRAPPER_BYTES)
        self.assertEqual(self._status(), WRAPPER_INSTALLED)

    def test_game_update_over_the_wrapper_is_reported_and_reinstall_keeps_it(self) -> None:
        # Steam put the updated game back under its own name, leaving the copy
        # the previous install moved aside.
        self.exe.write_bytes(b"MZ the updated game")
        self.original_exe.write_bytes(GAME_BYTES)
        self.assertEqual(self._status(), WRAPPER_MISSING)

        self._install()

        self.assertEqual(self.original_exe.read_bytes(), b"MZ the updated game")
        self.assertEqual(self.exe.read_bytes(), WRAPPER_BYTES)

    def test_reinstall_over_an_older_wrapper_keeps_the_game(self) -> None:
        self.exe.write_bytes(b"MZ older wrapper build " + WRAPPER_MARKER)
        self.original_exe.write_bytes(GAME_BYTES)
        self.assertEqual(self._status(), WRAPPER_INSTALLED)

        self._install()

        self.assertEqual(self.original_exe.read_bytes(), GAME_BYTES)
        self.assertEqual(self.exe.read_bytes(), WRAPPER_BYTES)

    def test_wrapper_without_the_game_is_not_reported_as_installed(self) -> None:
        self.exe.write_bytes(WRAPPER_BYTES)
        self.assertEqual(self._status(), WRAPPER_MISSING)

    def test_missing_game_executable_installs_nothing(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self._install()
        self.assertFalse(self.exe.exists())

    def test_refuses_a_wrapper_binary_it_could_not_recognise_later(self) -> None:
        self.exe.write_bytes(GAME_BYTES)
        self.wrapper.write_bytes(b"MZ something else")

        with self.assertRaises(RuntimeError):
            self._install()

        self.assertEqual(self.exe.read_bytes(), GAME_BYTES)
        self.assertFalse(self.original_exe.exists())

    def test_large_files_are_never_taken_for_the_wrapper(self) -> None:
        self.exe.write_bytes(WRAPPER_BYTES)
        with mock.patch("installers.assetto_wrapper_installer.WRAPPER_MAX_SIZE", len(WRAPPER_BYTES) - 1):
            self.assertFalse(is_wrapper_executable(self.exe))

    def test_marker_is_printed_by_the_wrapper_source(self) -> None:
        source = (ROOT / "assetto-wrapper" / "acpmf_wrapper.c").read_text(encoding="utf-8")
        self.assertIn(WRAPPER_MARKER.decode("ascii"), source)


if __name__ == "__main__":
    unittest.main()

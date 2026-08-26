import tempfile
import unittest
from pathlib import Path

from installers.ts_plugin_installer import (
    GAME_MISSING,
    PLUGIN_INSTALLED,
    PLUGIN_MISSING,
    discover_steam_libraries,
    find_plugin_binaries,
    install_ets2_plugins,
    install_ats_plugins,
    ts_plugin_status,
)
from installers.steam_utils import find_game_install_dirs


class TestTsPluginInstaller(unittest.TestCase):
    def test_discovers_libraryfolders_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Steam"
            extra = Path(temp_dir) / "Library"
            (root / "steamapps").mkdir(parents=True)
            (root / "steamapps/libraryfolders.vdf").write_text(
                f'"libraryfolders"\n{{\n  "1"\n  {{\n    "path"\t"{extra}"\n  }}\n}}\n',
                encoding="utf-8",
            )

            self.assertEqual(discover_steam_libraries([root]), [root, extra])

    def test_finds_ets2_install_dir_from_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Steam"
            steamapps = root / "steamapps"
            install_dir = steamapps / "common" / "Euro Truck Simulator 2"
            steamapps.mkdir(parents=True)
            (steamapps / "appmanifest_227300.acf").write_text("", encoding="utf-8")

            self.assertEqual(find_game_install_dirs("227300", "Euro Truck Simulator 2", [root]), [install_dir])

    def test_finds_ats_install_dir_from_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Steam"
            steamapps = root / "steamapps"
            install_dir = steamapps / "common" / "American Truck Simulator"
            steamapps.mkdir(parents=True)
            (steamapps / "appmanifest_270880.acf").write_text("", encoding="utf-8")

            self.assertEqual(find_game_install_dirs("270880", "American Truck Simulator", [root]), [install_dir])

    def test_finds_available_plugin_binaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            plugin_dir = app_dir / "scs-plugin"
            plugin_dir.mkdir()
            linux_plugin = plugin_dir / "logitech_rpm_telemetry.so"
            linux_plugin.write_bytes(b"plugin")

            self.assertEqual(find_plugin_binaries(app_dir), [("linux_x64", linux_plugin)])

    def test_installs_ets2_available_plugins(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Steam"
            steamapps = root / "steamapps"
            install_dir = steamapps / "common" / "Euro Truck Simulator 2"
            steamapps.mkdir(parents=True)
            install_dir.mkdir(parents=True)

            app_dir = Path(temp_dir) / "app"
            plugin_dir = app_dir / "scs-plugin"
            plugin_dir.mkdir(parents=True)
            linux_plugin = plugin_dir / "logitech_rpm_telemetry.so"
            windows_plugin = plugin_dir / "logitech_rpm_telemetry.dll"
            linux_plugin.write_bytes(b"linux")
            windows_plugin.write_bytes(b"windows")

            installed_paths = install_ets2_plugins(steam_roots=[root], app_dir=app_dir)

            expected_linux = install_dir / "bin/linux_x64/plugins/logitech_rpm_telemetry.so"
            expected_windows = install_dir / "bin/win_x64/plugins/logitech_rpm_telemetry.dll"
            self.assertEqual(installed_paths, [expected_linux, expected_windows])
            self.assertEqual(expected_linux.read_bytes(), b"linux")
            self.assertEqual(expected_windows.read_bytes(), b"windows")

    def test_installs_ats_available_plugins(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Steam"
            steamapps = root / "steamapps"
            install_dir = steamapps / "common" / "American Truck Simulator"
            steamapps.mkdir(parents=True)
            install_dir.mkdir(parents=True)

            app_dir = Path(temp_dir) / "app"
            plugin_dir = app_dir / "scs-plugin"
            plugin_dir.mkdir(parents=True)
            linux_plugin = plugin_dir / "logitech_rpm_telemetry.so"
            windows_plugin = plugin_dir / "logitech_rpm_telemetry.dll"
            linux_plugin.write_bytes(b"linux")
            windows_plugin.write_bytes(b"windows")

            installed_paths = install_ats_plugins(steam_roots=[root], app_dir=app_dir)

            expected_linux = install_dir / "bin/linux_x64/plugins/logitech_rpm_telemetry.so"
            expected_windows = install_dir / "bin/win_x64/plugins/logitech_rpm_telemetry.dll"
            self.assertEqual(installed_paths, [expected_linux, expected_windows])
            self.assertEqual(expected_linux.read_bytes(), b"linux")
            self.assertEqual(expected_windows.read_bytes(), b"windows")


class TestTsPluginStatus(unittest.TestCase):
    """The UI reports the plugin state before the user clicks Install."""

    ETS2 = ("227300", "Euro Truck Simulator 2")

    def _make_install_dir(self, temp_dir):
        root = Path(temp_dir) / "Steam"
        steamapps = root / "steamapps"
        install_dir = steamapps / "common" / self.ETS2[1]
        install_dir.mkdir(parents=True)
        return root, install_dir

    def test_reports_a_missing_game(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Steam"
            (root / "steamapps").mkdir(parents=True)

            self.assertEqual(ts_plugin_status(*self.ETS2, [root]), (GAME_MISSING, []))

    def test_reports_an_installed_game_without_the_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _install_dir = self._make_install_dir(temp_dir)

            self.assertEqual(ts_plugin_status(*self.ETS2, [root]), (PLUGIN_MISSING, []))

    def test_reports_the_installed_plugin_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, install_dir = self._make_install_dir(temp_dir)
            plugin = install_dir / "bin/linux_x64/plugins/logitech_rpm_telemetry.so"
            plugin.parent.mkdir(parents=True)
            plugin.write_bytes(b"linux")

            self.assertEqual(ts_plugin_status(*self.ETS2, [root]), (PLUGIN_INSTALLED, [plugin]))

    def test_status_sees_what_the_installer_just_wrote(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _install_dir = self._make_install_dir(temp_dir)
            app_dir = Path(temp_dir) / "app"
            plugin_dir = app_dir / "scs-plugin"
            plugin_dir.mkdir(parents=True)
            (plugin_dir / "logitech_rpm_telemetry.so").write_bytes(b"linux")
            (plugin_dir / "logitech_rpm_telemetry.dll").write_bytes(b"windows")

            installed_paths = install_ets2_plugins(steam_roots=[root], app_dir=app_dir)

            self.assertEqual(
                ts_plugin_status(*self.ETS2, [root]), (PLUGIN_INSTALLED, installed_paths)
            )


if __name__ == "__main__":
    unittest.main()

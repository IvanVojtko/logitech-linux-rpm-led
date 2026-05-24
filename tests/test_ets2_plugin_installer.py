import tempfile
import unittest
from pathlib import Path

from games.ets2_plugin_installer import (
    discover_steam_libraries,
    find_ets2_install_dirs,
    find_plugin_binaries,
    install_ets2_plugins,
)


class TestEts2PluginInstaller(unittest.TestCase):
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

            self.assertEqual(find_ets2_install_dirs([root]), [install_dir])

    def test_finds_available_plugin_binaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            plugin_dir = app_dir / "scs-plugin"
            plugin_dir.mkdir()
            linux_plugin = plugin_dir / "logitech_rpm_telemetry.so"
            linux_plugin.write_bytes(b"plugin")

            self.assertEqual(find_plugin_binaries(app_dir), [("linux_x64", linux_plugin)])

    def test_installs_available_plugins(self) -> None:
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


if __name__ == "__main__":
    unittest.main()

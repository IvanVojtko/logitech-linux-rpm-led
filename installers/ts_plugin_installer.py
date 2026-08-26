import shutil
from pathlib import Path

from installers.steam_utils import default_steam_roots, discover_steam_libraries, find_game_install_dirs

ETS2_APP_ID = "227300"
ETS2_DIR_NAME = "Euro Truck Simulator 2"
ATS_APP_ID = "270880"
ATS_DIR_NAME = "American Truck Simulator"
PLUGIN_DIR_NAME = "scs-plugin"
PLUGIN_FILENAMES = (
    ("linux_x64", "logitech_rpm_telemetry.so"),
    ("win_x64", "logitech_rpm_telemetry.dll"),
)


def find_plugin_binaries(app_dir=None):
    base_dir = Path(app_dir) if app_dir else Path(__file__).resolve().parents[1]
    plugin_dir = base_dir / PLUGIN_DIR_NAME
    binaries = []
    for platform_dir, filename in PLUGIN_FILENAMES:
        source = plugin_dir / filename
        if source.exists():
            binaries.append((platform_dir, source))
    return binaries


GAME_MISSING = "game-missing"
PLUGIN_MISSING = "plugin-missing"
PLUGIN_INSTALLED = "plugin-installed"


def plugin_destination(install_dir, platform_dir, filename):
    return Path(install_dir) / "bin" / platform_dir / "plugins" / filename


def ts_plugin_status(app_id, dir_name, steam_roots=None):
    """Report whether the telemetry plugin is already in place.

    Returns (state, installed_paths). The three states are distinct advice for
    the user: install the game, install the plugin, or nothing to do.
    """
    install_dirs = find_game_install_dirs(app_id, dir_name, steam_roots)
    if not install_dirs:
        return GAME_MISSING, []

    installed = []
    for install_dir in install_dirs:
        for platform_dir, filename in PLUGIN_FILENAMES:
            destination = plugin_destination(install_dir, platform_dir, filename)
            if destination.exists():
                installed.append(destination)

    return (PLUGIN_INSTALLED if installed else PLUGIN_MISSING), installed


def ets2_plugin_status(steam_roots=None):
    return ts_plugin_status(ETS2_APP_ID, ETS2_DIR_NAME, steam_roots)


def ats_plugin_status(steam_roots=None):
    return ts_plugin_status(ATS_APP_ID, ATS_DIR_NAME, steam_roots)


def install_ts_plugins(app_id, dir_name, steam_roots=None, app_dir=None):
    install_dirs = find_game_install_dirs(app_id, dir_name, steam_roots)
    if not install_dirs:
        raise FileNotFoundError(dir_name + " installation was not found in Steam libraries.")

    plugin_binaries = find_plugin_binaries(app_dir)
    if not plugin_binaries:
        raise FileNotFoundError("No built " + dir_name + " plugin binaries were found in scs-plugin/.")

    installed_paths = []
    for install_dir in install_dirs:
        for platform_dir, source in plugin_binaries:
            destination = plugin_destination(install_dir, platform_dir, source.name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            installed_paths.append(destination)

    return installed_paths


def install_ets2_plugins(steam_roots=None, app_dir=None):
    return install_ts_plugins(ETS2_APP_ID, ETS2_DIR_NAME, steam_roots, app_dir)


def install_ats_plugins(steam_roots=None, app_dir=None):
    return install_ts_plugins(ATS_APP_ID, ATS_DIR_NAME, steam_roots, app_dir)

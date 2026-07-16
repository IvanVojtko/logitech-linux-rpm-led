import os
import re
import shutil
from pathlib import Path

ETS2_APP_ID = "227300"
ETS2_DIR_NAME = "Euro Truck Simulator 2"
ATS_APP_ID = "270880"
ATS_DIR_NAME = "American Truck Simulator"
PLUGIN_DIR_NAME = "scs-plugin"
PLUGIN_FILENAMES = (
    ("linux_x64", "logitech_rpm_telemetry.so"),
    ("win_x64", "logitech_rpm_telemetry.dll"),
)


def default_steam_roots():
    home = Path.home()
    roots = [
        home / ".local/share/Steam",
        home / ".steam/steam",
        home / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
    ]
    env_root = os.environ.get("STEAM_DIR")
    if env_root:
        roots.insert(0, Path(env_root))
    return roots


def _normalize_vdf_path(raw_path):
    return raw_path.replace("\\\\", "\\")


def discover_steam_libraries(steam_roots=None):
    libraries = []
    seen = set()

    def add_library(path):
        resolved = Path(path).expanduser()
        key = str(resolved)
        if key not in seen:
            seen.add(key)
            libraries.append(resolved)

    for root in steam_roots or default_steam_roots():
        root = Path(root).expanduser()
        add_library(root)
        vdf_path = root / "steamapps/libraryfolders.vdf"
        try:
            content = vdf_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in re.finditer(r'"path"\s+"([^"]+)"', content):
            add_library(_normalize_vdf_path(match.group(1)))

    return libraries


def find_ts_install_dirs(app_id, dir_name, steam_roots=None):
    install_dirs = []
    seen = set()
    for library in discover_steam_libraries(steam_roots):
        steamapps = library / "steamapps"
        manifest = steamapps / f"appmanifest_{app_id}.acf"
        install_dir = steamapps / "common" / dir_name
        if not manifest.exists() and not install_dir.exists():
            continue
        key = str(install_dir)
        if key not in seen:
            seen.add(key)
            install_dirs.append(install_dir)
    return install_dirs


def find_plugin_binaries(app_dir=None):
    base_dir = Path(app_dir) if app_dir else Path(__file__).resolve().parents[1]
    plugin_dir = base_dir / PLUGIN_DIR_NAME
    binaries = []
    for platform_dir, filename in PLUGIN_FILENAMES:
        source = plugin_dir / filename
        if source.exists():
            binaries.append((platform_dir, source))
    return binaries


def install_ts_plugins(app_id, dir_name, steam_roots=None, app_dir=None):
    install_dirs = find_ts_install_dirs(app_id, dir_name, steam_roots)
    if not install_dirs:
        raise FileNotFoundError(dir_name + " installation was not found in Steam libraries.")

    plugin_binaries = find_plugin_binaries(app_dir)
    if not plugin_binaries:
        raise FileNotFoundError("No built " + dir_name + " plugin binaries were found in scs-plugin/.")

    installed_paths = []
    for install_dir in install_dirs:
        for platform_dir, source in plugin_binaries:
            destination_dir = install_dir / "bin" / platform_dir / "plugins"
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination = destination_dir / source.name
            shutil.copy2(source, destination)
            installed_paths.append(destination)

    return installed_paths


def install_ets2_plugins(steam_roots=None, app_dir=None):
    return install_ts_plugins(ETS2_APP_ID, ETS2_DIR_NAME, steam_roots, app_dir)


def install_ats_plugins(steam_roots=None, app_dir=None):
    return install_ts_plugins(ATS_APP_ID, ATS_DIR_NAME, steam_roots, app_dir)

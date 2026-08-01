import os
import re
from pathlib import Path

@staticmethod
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


@staticmethod
def _normalize_vdf_path(raw_path):
    return raw_path.replace("\\\\", "\\")


@staticmethod
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


@staticmethod
def find_game_install_dirs(app_id, dir_name, steam_roots=None):
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
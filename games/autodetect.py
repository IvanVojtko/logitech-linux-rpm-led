import os
from pathlib import Path

STEAM_APP_ID_KEYS = (
    b"SteamAppId=",
    b"STEAM_COMPAT_APP_ID=",
    b"SteamGameId=",
)

GAME_SIGNATURES = (
    {
        "key": "forza_horizon_5",
        "steam_app_ids": {"1551360"},
        "process_tokens": ("forzahorizon5.exe", "forza horizon 5"),
    },
    {
        "key": "f1_2019",
        "steam_app_ids": {"928600"},
        "process_tokens": ("f1_2019.exe",),
    },
    {
        "key": "f1_2020",
        "steam_app_ids": {"1080110"},
        "process_tokens": ("f1_2020.exe",),
    },
    {
        "key": "f1_2022",
        "steam_app_ids": {"1692250"},
        "process_tokens": ("f1_22.exe", "f1_2022.exe"),
    },
    {
        "key": "f1_2023",
        "steam_app_ids": {"2108330"},
        "process_tokens": ("f1_23.exe", "f1_2023.exe"),
    },
    {
        "key": "dirt_rally_2_0",
        "steam_app_ids": {"690790"},
        "process_tokens": ("dirtrally2.exe", "dirt rally 2.0"),
    },
    {
        "key": "ams_2",
        "steam_app_ids": {"1066890", "234630", "378860"},
        "process_tokens": (
            "ams2avx.exe",
            "ams2.exe",
            "pcars64.exe",
            "pcars2avx.exe",
            "project cars",
            "project cars 2",
        ),
    },
    {
        "key": "assetto_corsa",
        "steam_app_ids": {"244210"},
        "process_tokens": ("assettocorsa.exe", "assetto corsa"),
    },
)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore").strip().lower()
    except OSError:
        return ""


def _read_cmdline(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    parts = [part.decode("utf-8", errors="ignore") for part in raw.split(b"\0") if part]
    return " ".join(parts).lower()


def _read_steam_app_id(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    for entry in raw.split(b"\0"):
        for key in STEAM_APP_ID_KEYS:
            if entry.startswith(key):
                return entry[len(key):].decode("ascii", errors="ignore")
    return ""


def detect_game_from_processes(processes):
    for process in processes:
        app_id = process.get("steam_app_id", "")
        if not app_id:
            continue
        for signature in GAME_SIGNATURES:
            if app_id in signature["steam_app_ids"]:
                return signature["key"]

    for process in processes:
        name = process.get("name", "").lower()
        cmdline = process.get("cmdline", "").lower()
        haystack = f"{name} {cmdline}"
        for signature in GAME_SIGNATURES:
            for token in signature["process_tokens"]:
                if token in haystack:
                    return signature["key"]
    return None


def detect_running_game():
    proc_dir = Path("/proc")
    processes = []
    try:
        entries = os.scandir(proc_dir)
    except OSError:
        return None

    with entries as proc_entries:
        for entry in proc_entries:
            if not entry.name.isdigit():
                continue
            pid_path = proc_dir / entry.name
            processes.append(
                {
                    "name": _read_text(pid_path / "comm"),
                    "cmdline": _read_cmdline(pid_path / "cmdline"),
                    "steam_app_id": _read_steam_app_id(pid_path / "environ"),
                }
            )
    return detect_game_from_processes(processes)

import shutil
from pathlib import Path

from installers.steam_utils import default_steam_roots, discover_steam_libraries, find_game_install_dirs

ACC_APP_ID = "805550"
ACC_DIR_NAME = "Assetto Corsa Competizione"
ACC_SUBDIR_PATH = ""
ACC_EXE_NAME = "acc.exe"
ACR_APP_ID = "3917090"
ACR_DIR_NAME = "Assetto Corsa Rally"
ACR_SUBDIR_PATH = "acr/Binaries/Win64"
ACR_EXE_NAME = "acr.exe"
WRAPPER_DIR_NAME = "assetto-wrapper"
WRAPPER_FILE_NAME = "acpmf_wrapper.exe"


def find_wrapper_binary(app_dir=None):
    base_dir = Path(app_dir) if app_dir else Path(__file__).resolve().parents[1]
    wrapper_dir = base_dir / WRAPPER_DIR_NAME
    source = wrapper_dir / WRAPPER_FILE_NAME
    if source.exists():
        return source
    else:
        return None


GAME_MISSING = "game-missing"
WRAPPER_MISSING = "wrapper-missing"
WRAPPER_INSTALLED = "wrapper-installed"


def exe_destination(install_dir, relative_dir, filename):
    return Path(install_dir) / relative_dir / filename


def ac_wrapper_status(app_id, dir_name, subdir_path, exe_name, steam_roots=None):
    """Report whether the telemetry plugin is already in place.

    Returns (state, installed_paths). The three states are distinct advice for
    the user: install the game, install the plugin, or nothing to do.
    """
    install_dirs = find_game_install_dirs(app_id, dir_name, steam_roots)
    if not install_dirs:
        return GAME_MISSING, []

    installed = []
    for install_dir in install_dirs:
        destination = exe_destination(install_dir, subdir_path, "_" + exe_name)
        if destination.exists():
            installed.append(destination)

    return (WRAPPER_INSTALLED if installed else WRAPPER_MISSING), installed


def acc_wrapper_status(steam_roots=None):
    return ac_wrapper_status(ACC_APP_ID, ACC_DIR_NAME, ACC_SUBDIR_PATH, ACC_EXE_NAME, steam_roots)


def acr_wrapper_status(steam_roots=None):
    return ac_wrapper_status(ACR_APP_ID, ACR_DIR_NAME, ACR_SUBDIR_PATH, ACR_EXE_NAME, steam_roots)


def install_ac_wrapper(app_id, dir_name, subdir_path, exe_name, steam_roots=None, app_dir=None):
    install_dirs = find_game_install_dirs(app_id, dir_name, steam_roots)
    if not install_dirs:
        raise FileNotFoundError(dir_name + " installation was not found in Steam libraries.")

    wrapper_binary = find_wrapper_binary(app_dir)
    if wrapper_binary is None:
        raise FileNotFoundError("No built " + dir_name + " plugin binaries were found in assetto-wrapper/.")

    installed_paths = []
    for install_dir in install_dirs:
        exe_location = exe_destination(install_dir, subdir_path, exe_name)
        destination = exe_destination(install_dir, subdir_path, "_" + exe_name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Rename original game executable if it is not the case already
        if not Path(destination).exists():
            shutil.move(exe_location, destination)
        # Replace the game executable by the wrapper
        shutil.copy2(wrapper_binary, exe_location)
        installed_paths.append(destination)

    return installed_paths


def install_acc_wrapper(steam_roots=None, app_dir=None):
    return install_ac_wrapper(ACC_APP_ID, ACC_DIR_NAME, ACC_SUBDIR_PATH, ACC_EXE_NAME, steam_roots, app_dir)


def install_acr_wrapper(steam_roots=None, app_dir=None):
    return install_ac_wrapper(ACR_APP_ID, ACR_DIR_NAME, ACR_SUBDIR_PATH, ACR_EXE_NAME, steam_roots, app_dir)

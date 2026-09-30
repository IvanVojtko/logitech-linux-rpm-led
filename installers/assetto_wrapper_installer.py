import os
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
# Printed by acpmf_wrapper.c, so every build of the wrapper carries it and the
# games' own executables never do. Comparing against the bundled wrapper
# instead would mistake a wrapper from an older release for the game.
WRAPPER_MARKER = b"Bridged /dev/shm/"
# The wrapper is a few dozen KB; anything this big is a game, not worth reading.
WRAPPER_MAX_SIZE = 4 * 1024 * 1024


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


def is_wrapper_executable(path):
    try:
        if Path(path).stat().st_size > WRAPPER_MAX_SIZE:
            return False
        return WRAPPER_MARKER in Path(path).read_bytes()
    except OSError:
        return False


def ac_wrapper_status(app_id, dir_name, subdir_path, exe_name, steam_roots=None):
    """Report whether the wrapper is already in place.

    Returns (state, installed_paths). The three states are distinct advice for
    the user: install the game, install the wrapper, or nothing to do.

    The renamed original alone proves nothing: a Steam update puts the real
    game back under its own name and leaves that copy behind.
    """
    install_dirs = find_game_install_dirs(app_id, dir_name, steam_roots)
    if not install_dirs:
        return GAME_MISSING, []

    installed = []
    for install_dir in install_dirs:
        exe_location = exe_destination(install_dir, subdir_path, exe_name)
        original_exe = exe_destination(install_dir, subdir_path, "_" + exe_name)
        if is_wrapper_executable(exe_location) and original_exe.exists():
            installed.append(exe_location)

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
    if not is_wrapper_executable(wrapper_binary):
        # Installing it anyway would leave a wrapper the next install takes for
        # the game, and moves over the only copy of the real executable.
        raise RuntimeError(f"{wrapper_binary} does not look like the shared memory wrapper.")

    installed_paths = []
    for install_dir in install_dirs:
        exe_location = exe_destination(install_dir, subdir_path, exe_name)
        original_exe = exe_destination(install_dir, subdir_path, "_" + exe_name)
        # Anything under the game's own name that is not the wrapper is the
        # game -- also once a Steam update has put it back over the wrapper --
        # so it replaces whatever older copy the wrapper was launching.
        if exe_location.exists() and not is_wrapper_executable(exe_location):
            os.replace(exe_location, original_exe)
        if not original_exe.exists():
            raise FileNotFoundError(
                f"The {dir_name} executable was not found at {exe_location}. "
                "Verify the game files in Steam, then install the wrapper again."
            )
        shutil.copy2(wrapper_binary, exe_location)
        installed_paths.append(exe_location)

    return installed_paths


def install_acc_wrapper(steam_roots=None, app_dir=None):
    return install_ac_wrapper(ACC_APP_ID, ACC_DIR_NAME, ACC_SUBDIR_PATH, ACC_EXE_NAME, steam_roots, app_dir)


def install_acr_wrapper(steam_roots=None, app_dir=None):
    return install_ac_wrapper(ACR_APP_ID, ACR_DIR_NAME, ACR_SUBDIR_PATH, ACR_EXE_NAME, steam_roots, app_dir)

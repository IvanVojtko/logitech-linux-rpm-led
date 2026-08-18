# Logitech RPM LED Indicator (Linux)

Enable the RPM shift LEDs on a Logitech steering wheel while playing supported racing games on Linux.

This project listens to the game’s telemetry/UDP data output and drives the wheel RPM LED bar accordingly.

---

## Support

If you like my work, consider supporting me:

[![Support my work](https://img.buymeacoffee.com/button-api/?text=Support%20my%20work&emoji=&slug=ivanvojtko&button_colour=FF5F5F&font_colour=ffffff&font_family=Cookie&outline_colour=000000&coffee_colour=FFDD00)](https://www.buymeacoffee.com/ivanvojtko)

---

## Features

- RPM LED (shift light) support for Logitech wheels on Linux
- Simple UI: select game → Start
- Works with multiple telemetry formats (see supported games below)
- Auto-reconnect telemetry loop (recovers after game/launcher transitions)
- Optional auto-detect mode: switches selected game profile from running Steam game/process
- In auto-detect mode, telemetry stops automatically when no supported game is running
- Max RPM are persisted in `~/.config/logitech-rpm-indicator/settings.ini`
- Optional "Remember last selected game" restores the dropdown selection on app launch
- Shift-light RPM thresholds are user-configurable in UI and persisted in settings

---

## Supported games

- **Forza Horizon 5 / Forza Horizon 6**
- **F1 2019 / F1 2020 / F1 22 / F1 23**
- **DiRT Rally 2.0**
- **SMS Madness Engine games** (e.g., **Automobilista 2**, **Project CARS**, **Project CARS 2**)
- **Assetto Corsa** (manual max RPM input in app)
- **Assetto Corsa Competizione**
- **BeamNG.drive** (manual max RPM input in app)
- **Euro Truck Simulator 2 / American Truck Simulator** (requires the included SCS telemetry plugin)
- **Live for Speed** (manual max RPM input in app)
- **Wreckfest 2**

## Supported Wheels

Only the following Logitech wheels are supported at the moment.

- **G27**
- **G29**
- **G923, Xbox and Playstation variants**
- **G Pro, Xbox and Playstation variants** <ins>This is untested!</ins> Please open an issue if you encounter problems
- **RS50** <ins>This is untested!</ins> Please open an issue if you encounter problems.

---

## Installation

### Option A: Install from GitHub Releases (recommended)

1. Go to the project’s **Releases** page and download the latest package:
   - `*.deb` (Debian/Ubuntu)
   - `*.rpm` (Fedora/RHEL/openSUSE, etc.)

2. Install:

The binary packages declare runtime dependencies on distro repository packages
(`python3-hid`, PyGObject, Cairo, GTK 4, and libadwaita equivalents) and do not
install Python packages with `pip`.

**Debian/Ubuntu (.deb)**

```bash
sudo apt update
sudo apt install ./logitech-rpm-indicator.deb
```

**Fedora/RHEL/openSUSE (.rpm)**

```bash
sudo dnf install ./logitech-rpm-indicator.rpm
# or (depending on your distro)
sudo rpm -i ./logitech-rpm-indicator.rpm
```

3. Run the app (the command name typically matches the repository/package name):

```bash
logitech-rpm-indicator
```

> Tip: If you’re not sure what the command/package name is, list installed files:
>
> - Debian/Ubuntu: `dpkg -L logitech-rpm-indicator`
> - RPM: `rpm -ql logitech-rpm-indicator`

---

### Option B: Run from source

#### Requirements

- Python 3
- `pip`
- GTK 4, libadwaita, and GObject introspection development packages
- The native `hidapi` library (the `hid` package installed via `requirements.txt`
  is just a ctypes wrapper around it; without it the app can't see any wheel
  and won't report why)

On Debian/Ubuntu:

```bash
sudo apt install python3-dev libcairo2-dev libgirepository-2.0-dev gir1.2-gtk-4.0 gir1.2-adw-1 libhidapi-hidraw0
```

On Fedora:

```bash
sudo dnf install python3-devel cairo-devel gobject-introspection-devel gtk4-devel libadwaita-devel hidapi
```

On Gentoo:

```bash
sudo emerge --ask dev-libs/hidapi
```

#### Steps

```bash
python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

python main.py
```

### Option C: Install from source on other Linux distributions

The repository includes a distro-neutral `Makefile` for downstream packagers
and local source installs. Runtime dependencies must still be installed through
your distribution package manager.

Install under `/usr`:

```bash
sudo make install
```

Downstream packaging can stage files without modifying the host system:

```bash
make install DESTDIR="$pkgdir"
```

Override standard paths when required by a distribution:

```bash
make install DESTDIR="$pkgdir" PREFIX=/usr APPDIR=/usr/lib/logitech-rpm-indicator
```

The install target includes the desktop launcher, scalable SVG icon, `256x256`
PNG fallback, application sources, game artwork, and any ETS2 plugin binaries
that have already been built. Staged installs skip desktop cache refreshes;
package managers should run the provided `packaging/update-desktop-caches.sh`
hook after installation and removal.

---

## Usage

1. Connect your Logitech wheel.
2. Start the application:
   - From package install: `logitech-rpm-indicator`
   - From source: `python main.py`
3. Optional: enable **Auto-detect running game (Steam/process)** to auto-switch profiles.
4. Optional: enable **Remember last selected game** to restore the dropdown on startup.
5. Optional: tune **Shift LEDs (%)** thresholds to match your preferred shift-light band.
6. Select the game from the dropdown and click **Start**.
7. Launch the game and ensure telemetry output is enabled (instructions below).

---

## Game setup

### Forza Horizon 5 / Forza Horizon 6

1. Start **Forza Horizon 5** or **Forza Horizon 6**
2. Open **Settings → HUD**
3. Enable **Data Output**
4. Set:
   - **IP**: `127.0.0.1`
   - **Port**: `5300`

---

### F1 2019 / F1 2020 / F1 22 / F1 23

1. Open **Game Options → Settings → Telemetry Settings**
2. Set:
   - **UDP Telemetry**: `On`
   - **UDP Broadcast Mode**: `Off`
   - **UDP IP Address**: `127.0.0.1`
   - **Port**: `20777` (default)

---

### DiRT Rally 2.0

1. Edit the telemetry configuration file inside the Proton prefix:

```text
~/.local/share/Steam/steamapps/compatdata/690790/pfx/drive_c/users/steamuser/My Documents/My Games/DiRT Rally 2.0/hardwaresettings/hardware_settings_config.xml
```

2. Update these values:

- `udp enabled="true"`
- `extra_data="3"` (or `extra_data=3` depending on formatting)
- **UDP IP Address**: `127.0.0.1`
- **Port**: `20777`

> Note: The `compatdata/<id>` path may differ depending on your Steam library location and Proton setup.

---

### SMS Madness Engine (Automobilista 2 / Project CARS / Project CARS 2)

1. Go to **Options → System**
2. Set:
   - **Shared Memory**: `No`
   - **UDP Frequency**: `4`  
     (Lower number updates LEDs faster but increases CPU load)
   - **UDP Protocol Version**: `Project CARS 1`

---

### Assetto Corsa

1. Enable Assetto Corsa remote telemetry (UDP) in game settings.
2. In this app, select **Assetto Corsa** from the dropdown.
3. Set **Assetto Max RPM** in the input field to match your current car.
4. The value is saved automatically and restored on next launch.

---

### Assetto Corsa Competizione

You need to install the "wrapper" bridge between the "Windows" ACC shared
memory to a Linux one (/dev/shm):

1. In the ACC game folder, rename the file "acc.exe" to "_acc.exe"
2. Download <https://github.com/gotzl/pyacc/blob/main/linux/acc_wrapper.exe>
3. Move the downloaded file to the installation folder and rename
   it to "acc.exe"
4. Start the game as usual. A window should appear in addition to the game,
   with the text "Done! Waiting for ACC to stop." at the end.

---

### BeamNG

1. Open settings.
2. Select "Other" category.
3. Enable "OutGauge support", with default port "4444".

---

### Euro Truck Simulator 2 / American Truck Simulator

ETS2/ATS do not expose RPM telemetry directly over UDP. They loads native SCS
SDK plugins from the game directory, so this app includes a small plugin in
`scs-plugin/`. The plugin reads `truck.engine.rpm` and the truck `rpm.limit`
configuration value from the SCS Telemetry SDK, then forwards a local UDP packet
to this Python app on `127.0.0.1:5607`.

If you installed this app from a release package, select **Euro Truck Simulator
2 / American Truck Simulator** and click **Install ETS2 Telemetry Plugin** or
**Install ATS Telemetry Plugin**. The app searches your Steam libraries and
copies the bundled Linux/Windows plugin files into the ETS2/ATS `plugins`
directories.

If you run from source, build the plugin first:

Build the plugin:

```bash
curl -L https://download.eurotrucksimulator2.com/scs_sdk_1_14.zip -o /tmp/scs_sdk_1_14.zip
unzip /tmp/scs_sdk_1_14.zip -d /tmp/scs_sdk_1_14
make -C scs-plugin linux SCS_SDK_DIR=/tmp/scs_sdk_1_14
```

Copy `scs-plugin/logitech_rpm_telemetry.so` into the ETS2/ATS plugin directory:

```text
<SteamLibrary>/steamapps/common/Euro Truck Simulator 2/bin/linux_x64/plugins/
```

Create the `plugins` directory if it does not exist, then start ETS2/ATS and
select **Euro Truck Simulator 2 / American Truck Simulator** in this app.

For Proton/Windows ETS2/ATS, the same approach needs a Windows DLL build of the
plugin. Install a MinGW-w64 cross compiler, then run:

```bash
make -C scs-plugin windows SCS_SDK_DIR=/tmp/scs_sdk_1_14
```

Copy `scs-plugin/logitech_rpm_telemetry.dll` into:

```text
<SteamLibrary>/steamapps/common/Euro Truck Simulator 2/bin/win_x64/plugins/
```

or

```text
<SteamLibrary>/steamapps/common/American Truck Simulator/bin/win_x64/plugins/
```

On a system with both compilers installed, `make -C scs-plugin
SCS_SDK_DIR=/tmp/scs_sdk_1_14` builds both files.

---

### Live for Speed

1. Edit the telemetry configuration file inside the Wine prefix:

   `PREFIX_DIRECTORY/drive_c/LFS/cfg.txt`

2. Update these values:

   ```text
   OutGauge Mode 1
   OutGauge Delay 1
   OutGauge IP 127.0.0.1
   OutGauge Port 4444
   ```

   Set "Mode" value to "2" if you want RPM LEDs during replays.

> Note: The `LFS` location may differ depending on the path you chose during installation.

---

### Wreckfest 2

1. Edit the telemetry configuration file inside the Proton prefix:

```text
~/.local/share/Steam/steamapps/compatdata/1203190/pfx/drive_c/users/steamuser/My Documents/My Games/Wreckfest 2/1234512345123451234/savegame/telemetry/config.json
```

> Note: The `compatdata/<id>` path may differ depending on your Steam library location and Proton setup.

2. Update these values:

- `"enabled": 1`
- **IP Address**: `127.0.0.1`
- **Port**: `23123`

---

## Troubleshooting

### Nothing happens / LEDs don’t react

- Confirm the correct game is selected in the app and that you clicked **Start**
- Double-check telemetry is enabled in the game and IP/port match the instructions above
- Make sure no firewall rule is blocking localhost UDP (rare, but possible)

### Permission errors (Linux device access)

If you see a `PermissionError` when accessing the wheel device, you may need udev permissions.
A common approach is adding a udev rule for Logitech devices (vendor `046d`).

1. Find your device with:

```bash
lsusb
```

2. Create a udev rule (example):

```bash
sudo tee /etc/udev/rules.d/99-logitech-g29.rules >/dev/null <<'EOF'
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="046d", MODE="0666"
EOF
sudo udevadm control --reload-rules
sudo udevadm trigger
```

> If you prefer stricter permissions than `0666`, use a dedicated group and set `GROUP="..."` instead.

---

## License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

- See the full license text in [`LICENSE`](LICENSE).
- You may use, modify, and redistribute this software under the terms of GPL-3.0.
- If you distribute modified versions, you must also provide the corresponding source code under GPL-3.0.

SPDX identifier: `GPL-3.0-only`

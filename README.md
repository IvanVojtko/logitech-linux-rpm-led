# Logitech RPM LED Indicator (Linux)

Enable the RPM shift LEDs on a Logitech steering wheel while playing supported racing games on Linux.

This project listens to the game’s telemetry/UDP data output and drives the wheel RPM LED bar accordingly.

---

## Features

- RPM LED (shift light) support for Logitech wheels on Linux
- Simple UI: select game → Start
- Works with multiple telemetry formats (see supported games below)
- Auto-reconnect telemetry loop (recovers after game/launcher transitions)
- Optional auto-detect mode: switches selected game profile from running Steam game/process
- In auto-detect mode, telemetry stops automatically when no supported game is running
- Assetto Corsa max RPM is persisted in `~/.config/logitech-rpm-indicator/settings.ini`
- Optional "Remember last selected game" restores the dropdown selection on app launch
- Shift-light RPM thresholds are user-configurable in UI and persisted in settings

---

## Supported games

- **Forza Horizon 5**
- **F1 2019 / F1 2020 / F1 22 / F1 23**
- **DiRT Rally 2.0**
- **SMS Madness Engine games** (e.g., **Automobilista 2**, **Project CARS**, **Project CARS 2**)
- **Assetto Corsa** (manual max RPM input in app)
- **Euro Truck Simulator 2** (requires the included SCS telemetry plugin)

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

On Debian/Ubuntu:

```bash
sudo apt install python3-dev libcairo2-dev libgirepository-2.0-dev gir1.2-gtk-4.0 gir1.2-adw-1
```

On Fedora:

```bash
sudo dnf install python3-devel cairo-devel gobject-introspection-devel gtk4-devel libadwaita-devel
```

#### Steps

```bash
python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

python main.py
```

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

### Forza Horizon 5

1. Start **Forza Horizon 5**
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

### Euro Truck Simulator 2

ETS2 does not expose RPM telemetry directly over UDP. It loads native SCS SDK
plugins from the game directory, so this app includes a small plugin source in
`scs-plugin/`. The plugin reads `truck.engine.rpm` and the truck `rpm.limit`
configuration value from the SCS Telemetry SDK, then forwards a local UDP packet
to this Python app on `127.0.0.1:5607`.

Build and install the plugin:

```bash
curl -L https://download.eurotrucksimulator2.com/scs_sdk_1_14.zip -o /tmp/scs_sdk_1_14.zip
unzip /tmp/scs_sdk_1_14.zip -d /tmp/scs_sdk_1_14
make -C scs-plugin linux SCS_SDK_DIR=/tmp/scs_sdk_1_14
```

Copy `scs-plugin/logitech_rpm_telemetry.so` into the ETS2 plugin directory:

```text
<SteamLibrary>/steamapps/common/Euro Truck Simulator 2/bin/linux_x64/plugins/
```

Create the `plugins` directory if it does not exist, then start ETS2 and select
**Euro Truck Simulator 2** in this app.

For Proton/Windows ETS2, the same approach needs a Windows DLL build of the
plugin. Install a MinGW-w64 cross compiler, then run:

```bash
make -C scs-plugin windows SCS_SDK_DIR=/tmp/scs_sdk_1_14
```

Copy `scs-plugin/logitech_rpm_telemetry.dll` into:

```text
<SteamLibrary>/steamapps/common/Euro Truck Simulator 2/bin/win_x64/plugins/
```

On a system with both compilers installed, `make -C scs-plugin
SCS_SDK_DIR=/tmp/scs_sdk_1_14` builds both files.

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

## Support

If you like my work, consider supporting me:

[![Support my work](https://img.buymeacoffee.com/button-api/?text=Support%20my%20work&emoji=&slug=ivanvojtko&button_colour=FF5F5F&font_colour=ffffff&font_family=Cookie&outline_colour=000000&coffee_colour=FFDD00)](https://www.buymeacoffee.com/ivanvojtko)

---

## License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

- See the full license text in [`LICENSE`](LICENSE).
- You may use, modify, and redistribute this software under the terms of GPL-3.0.
- If you distribute modified versions, you must also provide the corresponding source code under GPL-3.0.

SPDX identifier: `GPL-3.0-only`

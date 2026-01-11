# Logitech RPM LED Indicator (Linux)

Enable the RPM shift LEDs on a Logitech steering wheel while playing supported racing games on Linux.

This project listens to the game’s telemetry/UDP data output and drives the wheel RPM LED bar accordingly.

---

## Features

- RPM LED (shift light) support for Logitech wheels on Linux
- Simple UI: select game → Start
- Works with multiple telemetry formats (see supported games below)

---

## Supported games

- **Forza Horizon 5**
- **F1 2019 / F1 2020 / F1 22 / F1 23**
- **DiRT Rally 2.0**
- **SMS Madness Engine games** (e.g., **Automobilista 2**, **Project CARS**, **Project CARS 2**)

---

## Installation

### Option A: Install from GitHub Releases (recommended)

1. Go to the project’s **Releases** page and download the latest package:
   - `*.deb` (Debian/Ubuntu)
   - `*.rpm` (Fedora/RHEL/openSUSE, etc.)

2. Install:

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
3. Select the game from the dropdown and click **Start**.
4. Launch the game and ensure telemetry output is enabled (instructions below).

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

# Logitech Forza RPM LED indicator
Enable RPM LED indicator on Logitech G29 steering wheel in Linux.

## Basic setup
1. Install Python dependencies `pip install -r requirements.tx`
2. Run script `python main.py`
3. Select game from dropdown menu and click Start

## How to run Forza Horizon 5
1. Start Forza Horizon 5
2. Go to settings / HUD
3. Enable data output
4. Set IP to `127.0.0.1` and port to `5300`

## How to run F1 2019
1. Open Game Options > Settings > Telemetry Settings
2. Set UDP Telemetry to On
3. Set UDP Broadcast Mode to Off
4. Set UDP IP Address to 127.0.0.1
5. Set Port to 20777 (default value)

## How to run F1 2023
1. Open Game Options > Settings > Telemetry Settings
2. Set UDP Telemetry to On
3. Set UDP Broadcast Mode to Off
4. Set UDP IP Address to 127.0.0.1
5. Set Port to 20777 (default value)

## How to run Dirt Rally 2.0
1. Edit file ~/.local/share/Steam/steamapps/compatdata/690790/pfx/drive_c/users/steamuser/My Documents/My Games/DiRT Rally 2.0/hardwaresettings/hardware_settings_config.xml
2. Set udp enabled="true"
3. Set extra_data=3
4. Set UDP IP Address to 127.0.0.1
5. Set Port to 20777

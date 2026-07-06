import sys
import time
import socket
import os
import configparser
from pathlib import Path

import gi
import threading
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject, Gdk, GLib

from games.forza_horizon import ForzaHorizon5, ForzaHorizon6
from games.f12019 import F12019
from games.f12020 import F12020
from games.f12022 import F12022
from games.f12023 import F12023
from games.dirt_rally_2_0 import DirtRally2
from games.automobilista_2 import Automobilista2
from games.assetto_corsa import AssettoCorsa
from games.euro_truck_simulator_2 import EuroTruckSimulator2
from games.ets2_plugin_installer import install_ets2_plugins
from games.wreckfest_2 import Wreckfest2
from games.autodetect import detect_running_game
from wheels.base import BaseWheel
from wheels.detect import find_wheel

APP_DIR = Path(__file__).resolve().parent
ICONS_DIR = APP_DIR / "icons"
APPLICATION_ID = "io.github.IvanVojtko.LogitechRpmIndicator"

AMS_2 =             0
ASSETTO_CORSA =     1
DIRT_RALLY_2_0 =    2
F1_2019 =           3
F1_2020 =           4
F1_2022 =           5
F1_2023 =           6
FORZA_HORIZON_5 =   7
FORZA_HORIZON_6 =   8
EURO_TRUCK_SIMULATOR_2 = 9
WRECKFEST_2 =       10

DEFAULT_ASSETTO_MAX_RPM = 9000
MIN_ASSETTO_MAX_RPM = 1000
MAX_ASSETTO_MAX_RPM = 20000
RECONNECT_DELAY_SECONDS = 1.0
RECONNECT_INACTIVITY_SECONDS = 3.0
AUTO_DETECT_INTERVAL_SECONDS = 1.0
DEFAULT_REMEMBER_LAST_GAME = False
DEFAULT_LAST_SELECTED_GAME = AMS_2
SHIFT_LIGHT_THRESHOLD_COUNT = 5

GAME_KEY_TO_CHOICE = {
    "ams_2": AMS_2,
    "assetto_corsa": ASSETTO_CORSA,
    "dirt_rally_2_0": DIRT_RALLY_2_0,
    "f1_2019": F1_2019,
    "f1_2020": F1_2020,
    "f1_2022": F1_2022,
    "f1_2023": F1_2023,
    "forza_horizon_5": FORZA_HORIZON_5,
    "forza_horizon_6": FORZA_HORIZON_6,
    "euro_truck_simulator_2": EURO_TRUCK_SIMULATOR_2,
    "wreckfest_2": WRECKFEST_2,
}


def icon_path(filename):
    return str(ICONS_DIR / filename)

APP_CSS = """
.rpm-window {
  background-image: linear-gradient(140deg, alpha(#183152, 0.09), alpha(#1f5f6d, 0.10));
}

.title-label {
  font-size: 27px;
  font-weight: 800;
}

.subtitle-label {
  opacity: 0.82;
}

.panel {
  background-color: alpha(@theme_bg_color, 0.94);
  border-radius: 14px;
  border: 1px solid alpha(@theme_fg_color, 0.10);
  padding: 16px;
}

.section-title {
  font-weight: 700;
  letter-spacing: 0.05em;
  opacity: 0.88;
}

.status-caption {
  opacity: 0.8;
}

.status-value {
  font-weight: 700;
}

.action-button {
  min-height: 40px;
}

.success-label {
  color: #2f8f46;
}

.warning-label {
  color: #b26a00;
}

.rpm-meter {
  min-height: 18px;
}

.rpm-preview-label {
  font-size: 24px;
  font-weight: 800;
}

.led-segment {
  min-width: 52px;
  min-height: 12px;
  border-radius: 999px;
  background-color: alpha(@theme_fg_color, 0.16);
}

.led-segment.active {
  background-color: #e4534d;
}
"""


class Widget(Gtk.Box):
    __gtype_name__ = 'Widget'

    def __init__(self, name, image_path):
        super().__init__()
        self._name = name

        # Create an image widget
        self._image = image_path

    @GObject.Property
    def name(self):
        return self._name

    @GObject.Property
    def image(self):
        return self._image


class WheelRPMWindow(Gtk.ApplicationWindow):
    _css_loaded = False

    def __init__(self, *args, **kwargs):
        # Create the main window
        super().__init__(*args, **kwargs)

        self.thread = None
        self.stop_event = threading.Event()
        self.running = False
        self.shared_rpm_percent = 0
        self.active_game_choice = None
        self.auto_detect_enabled = False
        self.remember_last_selected_game = DEFAULT_REMEMBER_LAST_GAME
        self.last_selected_game_choice = DEFAULT_LAST_SELECTED_GAME
        self.last_auto_detect_check = 0.0
        self.settings_path = self._get_settings_path()
        self.assetto_max_rpm = DEFAULT_ASSETTO_MAX_RPM
        self.shift_light_thresholds = tuple(BaseWheel.DEFAULT_SHIFT_LIGHT_THRESHOLDS)
        self._updating_shift_light_inputs = False
        self._load_settings()
        self.shift_light_thresholds = BaseWheel.set_shift_light_thresholds(self.shift_light_thresholds)

        self._ensure_css()
        self.add_css_class("rpm-window")
        self.set_title("Logitech RPM LED indicator")
        self.set_default_size(560, 350)
        self.set_size_request(460, 300)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        root.set_margin_top(24)
        root.set_margin_bottom(24)
        root.set_margin_start(24)
        root.set_margin_end(24)
        self.set_child(root)

        title = Gtk.Label(label="RPM LED Telemetry")
        title.add_css_class("title-label")
        title.set_xalign(0)
        subtitle = Gtk.Label(
            label="Pick a game source and stream rev lights to your Logitech wheel, or use the preview without hardware."
        )
        subtitle.add_css_class("subtitle-label")
        subtitle.set_xalign(0)
        subtitle.set_wrap(True)
        root.append(title)
        root.append(subtitle)

        game_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        game_panel.add_css_class("panel")
        root.append(game_panel)

        game_title = Gtk.Label(label="GAME SOURCE")
        game_title.add_css_class("section-title")
        game_title.set_xalign(0)
        game_panel.append(game_title)

        # Create factory
        factory_widget = Gtk.SignalListItemFactory()
        factory_widget.connect("setup", self._on_factory_widget_setup)
        factory_widget.connect("bind", self._on_factory_widget_bind)

        # Create a dropdown (Gtk.ComboBoxText)
        self.model_widget = Gio.ListStore(item_type=Widget)
        self.model_widget.append(Widget(name="AMS 2 / pCars / pCars2", image_path=icon_path("ams-2.png")))
        self.model_widget.append(Widget(name="Assetto Corsa", image_path=icon_path("asseto.png")))
        self.model_widget.append(Widget(name="Dirt Rally 2.0", image_path=icon_path("dirt-rally-2-0.png")))
        self.model_widget.append(Widget(name="F1 2019", image_path=icon_path("f1-2019.png")))
        self.model_widget.append(Widget(name="F1 2020", image_path=icon_path("f1-2020.png")))
        self.model_widget.append(Widget(name="F1 2022", image_path=icon_path("f1-2022.png")))
        self.model_widget.append(Widget(name="F1 2023", image_path=icon_path("f1-2023.png")))
        self.model_widget.append(Widget(name="Forza Horizon 5", image_path=icon_path("forza-horizon-5.png")))
        self.model_widget.append(Widget(name="Forza Horizon 6", image_path=icon_path("forza-horizon-5.png")))
        self.model_widget.append(Widget(name="Euro Truck Simulator 2", image_path=icon_path("ams-2.png")))
        self.model_widget.append(Widget(name="Wreckfest 2", image_path=icon_path("wreckfest-2.png")))
        self.combo = Gtk.DropDown(model=self.model_widget, factory=factory_widget)
        self.combo.set_hexpand(True)
        self.combo.set_enable_search(True)
        game_panel.append(self.combo)
        self.combo.connect("notify::selected", self._on_game_selected_changed)

        self.auto_detect_checkbox = Gtk.CheckButton(label="Auto-detect running game (Steam/process)")
        self.auto_detect_checkbox.set_active(self.auto_detect_enabled)
        self.auto_detect_checkbox.connect("toggled", self._on_auto_detect_toggled)
        game_panel.append(self.auto_detect_checkbox)

        self.remember_last_game_checkbox = Gtk.CheckButton(label="Remember last selected game")
        self.remember_last_game_checkbox.set_active(self.remember_last_selected_game)
        self.remember_last_game_checkbox.connect("toggled", self._on_remember_last_game_toggled)
        game_panel.append(self.remember_last_game_checkbox)

        if self.remember_last_selected_game and self._is_valid_choice(self.last_selected_game_choice):
            self.combo.set_selected(self.last_selected_game_choice)

        self.shift_light_threshold_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.shift_light_threshold_label = Gtk.Label(label="Shift LEDs (%)")
        self.shift_light_threshold_label.set_xalign(0)
        self.shift_light_threshold_label.set_hexpand(True)
        self.shift_light_threshold_row.append(self.shift_light_threshold_label)
        self.shift_light_threshold_inputs = []
        for index, threshold in enumerate(self.shift_light_thresholds):
            threshold_input = Gtk.SpinButton.new_with_range(0, 100, 1)
            threshold_input.set_numeric(True)
            threshold_input.set_width_chars(3)
            threshold_input.set_value(threshold)
            threshold_input.set_tooltip_text(f"LED {index + 1} threshold")
            threshold_input.connect("value-changed", self._on_shift_light_threshold_changed, index)
            self.shift_light_threshold_inputs.append(threshold_input)
            self.shift_light_threshold_row.append(threshold_input)
        game_panel.append(self.shift_light_threshold_row)

        self.assetto_max_rpm_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.assetto_max_rpm_label = Gtk.Label(label="Assetto Max RPM")
        self.assetto_max_rpm_label.set_xalign(0)
        self.assetto_max_rpm_label.set_hexpand(True)
        self.assetto_max_rpm_input = Gtk.SpinButton.new_with_range(
            MIN_ASSETTO_MAX_RPM, MAX_ASSETTO_MAX_RPM, 100
        )
        self.assetto_max_rpm_input.set_numeric(True)
        self.assetto_max_rpm_input.set_value(self.assetto_max_rpm)
        self.assetto_max_rpm_input.connect("value-changed", self._on_assetto_max_rpm_changed)
        self.assetto_max_rpm_row.append(self.assetto_max_rpm_label)
        self.assetto_max_rpm_row.append(self.assetto_max_rpm_input)
        self.assetto_max_rpm_row.set_visible(False)
        game_panel.append(self.assetto_max_rpm_row)

        self.ets2_plugin_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.ets2_plugin_button = Gtk.Button(label="Install ETS2 Telemetry Plugin")
        self.ets2_plugin_button.add_css_class("action-button")
        self.ets2_plugin_button.connect("clicked", self._on_ets2_plugin_install_clicked)
        self.ets2_plugin_status = Gtk.Label()
        self.ets2_plugin_status.set_xalign(0)
        self.ets2_plugin_status.set_wrap(True)
        self.ets2_plugin_box.append(self.ets2_plugin_button)
        self.ets2_plugin_box.append(self.ets2_plugin_status)
        self.ets2_plugin_box.set_visible(False)
        game_panel.append(self.ets2_plugin_box)

        self.wheel = find_wheel()
        if not self.wheel:
            print("No supported Logitech wheel found.")

        self.start_button = Gtk.Button(label="Start Telemetry")
        self.start_button.add_css_class("suggested-action")
        self.start_button.add_css_class("action-button")
        self.start_button.connect("clicked", self.on_button_clicked)
        game_panel.append(self.start_button)

        status_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        status_panel.add_css_class("panel")
        root.append(status_panel)

        status_title = Gtk.Label(label="STATUS")
        status_title.add_css_class("section-title")
        status_title.set_xalign(0)
        status_panel.append(status_title)

        wheel_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._append_status_caption(wheel_row, "Wheel")
        self.wheel_status_icon = Gtk.Image()
        self.wheel_status_text = Gtk.Label()
        self.wheel_status_text.add_css_class("status-value")
        self._append_status_value(wheel_row, self.wheel_status_icon, self.wheel_status_text)
        status_panel.append(wheel_row)

        session_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._append_status_caption(session_row, "Session")
        self.session_status_icon = Gtk.Image.new_from_icon_name("media-playback-stop-symbolic")
        self.session_status_text = Gtk.Label(label="Idle")
        self.session_status_text.add_css_class("status-value")
        self._append_status_value(session_row, self.session_status_icon, self.session_status_text)
        status_panel.append(session_row)

        rpm_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._append_status_caption(rpm_row, "RPM")
        self.rpm_percent_text = Gtk.Label(label="0%")
        self.rpm_percent_text.add_css_class("rpm-preview-label")
        self._append_status_value(rpm_row, Gtk.Image(), self.rpm_percent_text)
        status_panel.append(rpm_row)

        self.rpm_meter = Gtk.ProgressBar()
        self.rpm_meter.set_hexpand(True)
        self.rpm_meter.add_css_class("rpm-meter")
        self.rpm_meter.set_show_text(True)
        self.rpm_meter.set_text("0%")
        status_panel.append(self.rpm_meter)

        self.rpm_led_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.rpm_led_row.set_halign(Gtk.Align.FILL)
        self.rpm_leds = []
        for _ in range(5):
            led = Gtk.Box()
            led.add_css_class("led-segment")
            self.rpm_led_row.append(led)
            self.rpm_leds.append(led)
        status_panel.append(self.rpm_led_row)

        self._update_wheel_status()
        self._update_running_status()
        self._update_rpm_preview(0)
        self._on_game_selected_changed()
        GLib.timeout_add(80, self._refresh_process_state)
        self.connect("close-request", self._on_close_request)

    def _append_status_caption(self, row, text):
        caption = Gtk.Label(label=text)
        caption.add_css_class("status-caption")
        caption.set_xalign(0)
        caption.set_hexpand(True)
        row.append(caption)

    def _append_status_value(self, row, icon, label):
        value_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        value_box.set_halign(Gtk.Align.END)
        value_box.append(icon)
        value_box.append(label)
        row.append(value_box)

    def _is_valid_choice(self, choice):
        if choice == Gtk.INVALID_LIST_POSITION:
            return False
        return 0 <= int(choice) < self.model_widget.get_n_items()

    @staticmethod
    def _get_settings_path():
        config_home = os.environ.get("XDG_CONFIG_HOME")
        if config_home:
            base_dir = Path(config_home)
        else:
            base_dir = Path.home() / ".config"
        return base_dir / "logitech-rpm-indicator" / "settings.ini"

    @staticmethod
    def _serialize_shift_light_thresholds(thresholds):
        return ",".join(str(int(threshold)) for threshold in thresholds)

    @staticmethod
    def _parse_shift_light_thresholds(raw_value):
        try:
            parsed = [int(part.strip()) for part in raw_value.split(",") if part.strip() != ""]
        except ValueError:
            return tuple(BaseWheel.DEFAULT_SHIFT_LIGHT_THRESHOLDS)
        if len(parsed) != SHIFT_LIGHT_THRESHOLD_COUNT:
            return tuple(BaseWheel.DEFAULT_SHIFT_LIGHT_THRESHOLDS)
        return tuple(parsed)

    def _load_settings(self):
        parser = configparser.ConfigParser()
        if not self.settings_path.exists():
            return
        try:
            parser.read(self.settings_path, encoding="utf-8")
            self.auto_detect_enabled = parser.getboolean(
                "general", "auto_detect", fallback=False
            )
            self.remember_last_selected_game = parser.getboolean(
                "general", "remember_last_game", fallback=DEFAULT_REMEMBER_LAST_GAME
            )
            self.last_selected_game_choice = parser.getint(
                "general", "last_selected_game", fallback=DEFAULT_LAST_SELECTED_GAME
            )
            value = parser.getint(
                "assetto_corsa", "max_rpm", fallback=DEFAULT_ASSETTO_MAX_RPM
            )
            self.assetto_max_rpm = max(MIN_ASSETTO_MAX_RPM, min(value, MAX_ASSETTO_MAX_RPM))
            shift_thresholds_raw = parser.get(
                "shift_lights",
                "thresholds",
                fallback=self._serialize_shift_light_thresholds(BaseWheel.DEFAULT_SHIFT_LIGHT_THRESHOLDS),
            )
            self.shift_light_thresholds = self._parse_shift_light_thresholds(shift_thresholds_raw)
        except Exception as exc:
            print(f"Failed to read settings: {exc}")

    def _save_settings(self):
        parser = configparser.ConfigParser()
        parser["general"] = {
            "auto_detect": str(self.auto_detect_enabled).lower(),
            "remember_last_game": str(self.remember_last_selected_game).lower(),
            "last_selected_game": str(int(self.last_selected_game_choice)),
        }
        parser["assetto_corsa"] = {"max_rpm": str(int(self.assetto_max_rpm))}
        parser["shift_lights"] = {
            "thresholds": self._serialize_shift_light_thresholds(self.shift_light_thresholds)
        }
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            with self.settings_path.open("w", encoding="utf-8") as settings_file:
                parser.write(settings_file)
        except Exception as exc:
            print(f"Failed to write settings: {exc}")

    def _set_shift_light_thresholds(self, thresholds, save=True):
        self.shift_light_thresholds = BaseWheel.set_shift_light_thresholds(thresholds)
        self._sync_shift_light_threshold_inputs()
        display_percent = self.shared_rpm_percent if self.running else 0
        self._update_rpm_preview(display_percent)
        if save:
            self._save_settings()

    def _sync_shift_light_threshold_inputs(self):
        if not hasattr(self, "shift_light_threshold_inputs"):
            return
        self._updating_shift_light_inputs = True
        try:
            for threshold_input, threshold in zip(self.shift_light_threshold_inputs, self.shift_light_thresholds):
                if int(threshold_input.get_value()) != int(threshold):
                    threshold_input.set_value(int(threshold))
        finally:
            self._updating_shift_light_inputs = False

    def _on_assetto_max_rpm_changed(self, _spin):
        self.assetto_max_rpm = int(self.assetto_max_rpm_input.get_value())
        self._save_settings()

    def _on_auto_detect_toggled(self, _checkbox):
        self.auto_detect_enabled = self.auto_detect_checkbox.get_active()
        self.last_auto_detect_check = 0.0
        self._save_settings()

    def _on_remember_last_game_toggled(self, _checkbox):
        self.remember_last_selected_game = self.remember_last_game_checkbox.get_active()
        if self._is_valid_choice(self.combo.get_selected()):
            self.last_selected_game_choice = int(self.combo.get_selected())
        self._save_settings()

    def _on_shift_light_threshold_changed(self, _spin, _index):
        if self._updating_shift_light_inputs:
            return
        thresholds = [int(input_widget.get_value()) for input_widget in self.shift_light_threshold_inputs]
        self._set_shift_light_thresholds(thresholds, save=True)

    def _update_wheel_status(self):
        if self.wheel:
            self.wheel_status_icon.set_from_icon_name("emblem-ok-symbolic")
            self.wheel_status_text.set_text("Detected")
            return
        self.wheel_status_icon.set_from_icon_name("dialog-warning-symbolic")
        self.wheel_status_text.set_text("Not detected (preview only)")

    def _on_game_selected_changed(self, *_args):
        selected_choice = self.combo.get_selected()
        self.assetto_max_rpm_row.set_visible(selected_choice == ASSETTO_CORSA)
        self.ets2_plugin_box.set_visible(selected_choice == EURO_TRUCK_SIMULATOR_2)
        if self._is_valid_choice(selected_choice):
            self.last_selected_game_choice = int(selected_choice)
            if self.remember_last_selected_game:
                self._save_settings()

    def _set_ets2_plugin_status(self, message, css_class):
        self.ets2_plugin_status.remove_css_class("success-label")
        self.ets2_plugin_status.remove_css_class("warning-label")
        self.ets2_plugin_status.add_css_class(css_class)
        self.ets2_plugin_status.set_text(message)

    def _on_ets2_plugin_install_clicked(self, _button):
        self.ets2_plugin_button.set_sensitive(False)
        try:
            installed_paths = install_ets2_plugins(app_dir=Path(__file__).resolve().parent)
            if not installed_paths:
                self._set_ets2_plugin_status("No ETS2 plugin files were installed.", "warning-label")
                return
            self._set_ets2_plugin_status(
                f"Installed {len(installed_paths)} ETS2 plugin file(s). Restart ETS2 if it is already running.",
                "success-label",
            )
        except Exception as exc:
            self._set_ets2_plugin_status(str(exc), "warning-label")
        finally:
            self.ets2_plugin_button.set_sensitive(True)

    @staticmethod
    def _percent_to_led_bits(percent):
        return BaseWheel._percent_to_bits(percent)

    def _update_rpm_preview(self, percent):
        clamped = max(0, min(int(percent), 100))
        self.rpm_percent_text.set_text(f"{clamped}%")
        self.rpm_meter.set_fraction(clamped / 100)
        self.rpm_meter.set_text(f"{clamped}%")
        bits = self._percent_to_led_bits(clamped)
        for index, led in enumerate(self.rpm_leds):
            if bits & (1 << index):
                led.add_css_class("active")
            else:
                led.remove_css_class("active")

    def _update_running_status(self):
        if self.running:
            self.session_status_icon.set_from_icon_name("media-playback-start-symbolic")
            self.session_status_text.set_text("Running")
            self.start_button.set_label("Stop Telemetry")
            self.start_button.remove_css_class("suggested-action")
            self.start_button.add_css_class("destructive-action")
            return
        self.session_status_icon.set_from_icon_name("media-playback-stop-symbolic")
        self.session_status_text.set_text("Idle")
        self.start_button.set_label("Start Telemetry")
        self.start_button.remove_css_class("destructive-action")
        self.start_button.add_css_class("suggested-action")

    def _refresh_process_state(self):
        if self.running and (self.thread is None or not self.thread.is_alive()):
            self.running = False
            self.thread = None
            self.active_game_choice = None
            self._update_running_status()
            self.shared_rpm_percent = 0
        self._run_auto_detect_cycle()
        display_percent = self.shared_rpm_percent if self.running else 0
        self._update_rpm_preview(display_percent)
        return True

    def _stop_telemetry(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.wheel:
            self.wheel.leds_rpm(0)
        self.shared_rpm_percent = 0
        self._update_rpm_preview(0)
        self.thread = None
        self.active_game_choice = None
        self.running = False

    def _on_close_request(self, _window):
        self.assetto_max_rpm = int(self.assetto_max_rpm_input.get_value())
        self._save_settings()
        self._stop_telemetry()
        return False

    def _ensure_css(self):
        if WheelRPMWindow._css_loaded:
            return
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(APP_CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        WheelRPMWindow._css_loaded = True

    def _create_game_from_choice(self, choice):
        if choice == FORZA_HORIZON_5:
            return ForzaHorizon5()
        if choice == FORZA_HORIZON_6:
            return ForzaHorizon6()
        if choice == F1_2019:
            return F12019()
        if choice == F1_2020:
            return F12020()
        if choice == F1_2022:
            return F12022()
        if choice == F1_2023:
            return F12023()
        if choice == DIRT_RALLY_2_0:
            return DirtRally2()
        if choice == AMS_2:
            return Automobilista2()
        if choice == ASSETTO_CORSA:
            self.assetto_max_rpm = int(self.assetto_max_rpm_input.get_value())
            self._save_settings()
            return AssettoCorsa(max_rpm=self.assetto_max_rpm)
        if choice == EURO_TRUCK_SIMULATOR_2:
            return EuroTruckSimulator2()
        if choice == WRECKFEST_2:
            return Wreckfest2()
        return None

    def _start_telemetry_for_choice(self, choice):
        game = self._create_game_from_choice(choice)
        if game is None:
            print("No game selected.")
            return False

        self.running = True
        self.stop_event.clear()
        self.shared_rpm_percent = 0
        self.active_game_choice = choice
        self.thread = threading.Thread(
            target=self.game_handling_loop,
            args=(game, self.wheel, choice),
            daemon=True,
        )
        self.thread.start()
        self._update_running_status()
        return True

    def _run_auto_detect_cycle(self):
        if not self.auto_detect_enabled:
            return

        now = time.monotonic()
        if now - self.last_auto_detect_check < AUTO_DETECT_INTERVAL_SECONDS:
            return
        self.last_auto_detect_check = now

        detected_game_key = detect_running_game()
        detected_choice = GAME_KEY_TO_CHOICE.get(detected_game_key)
        if detected_choice is None:
            if self.running and self.active_game_choice is not None:
                self._stop_telemetry()
                self._update_running_status()
            return

        if self.combo.get_selected() != detected_choice:
            self.combo.set_selected(detected_choice)

        if not self.running:
            self._start_telemetry_for_choice(detected_choice)
            return

        if self.active_game_choice != detected_choice:
            self._stop_telemetry()
            self._update_running_status()
            self._start_telemetry_for_choice(detected_choice)

    def on_button_clicked(self, _button):
        if self.running and (self.thread is None or not self.thread.is_alive()):
            self.running = False
            self.thread = None
            self.active_game_choice = None
            self._update_running_status()
            self.shared_rpm_percent = 0
            self._update_rpm_preview(0)

        if not self.running:
            self._start_telemetry_for_choice(self.combo.get_selected())
        else:
            self._stop_telemetry()
            self._update_running_status()

    def game_handling_loop(self, game, wheel, choice):
        if game is None:
            return

        udp_socket = None
        percent = 0
        last_send = 0.0
        last_packet_time = 0.0
        next_reconnect_time = 0.0
        while not self.stop_event.is_set():
            now = time.monotonic()
            if udp_socket is None:
                if now < next_reconnect_time:
                    time.sleep(0.05)
                    continue
                try:
                    udp_socket = game.connect()
                    udp_socket.settimeout(0.2)
                    last_packet_time = time.monotonic()
                    self.shared_rpm_percent = 0
                    percent = 0
                    print("Telemetry connection established.")
                except Exception as exc:
                    print(f"Telemetry connect failed: {exc}")
                    self.shared_rpm_percent = 0
                    next_reconnect_time = now + RECONNECT_DELAY_SECONDS
                    time.sleep(0.05)
                    continue

            try:
                data = game.read_data(udp_socket=udp_socket)
            except socket.timeout:
                if (
                    time.monotonic() - last_packet_time
                    >= RECONNECT_INACTIVITY_SECONDS
                ):
                    udp_socket = self._close_game_socket(game, udp_socket)
                    next_reconnect_time = time.monotonic() + RECONNECT_DELAY_SECONDS
                continue
            except Exception as exc:
                print(f"Telemetry read failed, reconnecting: {exc}")
                udp_socket = self._close_game_socket(game, udp_socket)
                next_reconnect_time = time.monotonic() + RECONNECT_DELAY_SECONDS
                continue

            last_packet_time = time.monotonic()
            if choice in (FORZA_HORIZON_5, FORZA_HORIZON_6):
                max_rpm, current_rpm = game.parse_rpm(data=data)
                percent = game.get_rpm_percent(max_rpm=max_rpm, current_rpm=current_rpm)
            else:
                percent = game.get_rpm_percent(data, percent)
            clamped_percent = max(0, min(int(percent), 100))
            self.shared_rpm_percent = clamped_percent
            now = time.perf_counter()
            if now - last_send >= 0.05:
                if wheel:
                    wheel.leds_rpm(clamped_percent if clamped_percent != 0 else 0)
                last_send = now

        self.shared_rpm_percent = 0
        try:
            if wheel:
                wheel.leds_rpm(0)
        except Exception:
            pass
        self._close_game_socket(game, udp_socket)

    @staticmethod
    def _close_game_socket(game, udp_socket):
        if not udp_socket:
            return None
        try:
            disconnect = getattr(game, "disconnect", None)
            if callable(disconnect):
                disconnect(udp_socket)
        except Exception:
            pass
        try:
            udp_socket.close()
        except Exception:
            pass
        return None

    def _on_factory_widget_setup(self, factory, list_item):
        box = Gtk.Box(spacing=8, orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label()
        label.set_xalign(0)
        image = Gtk.Image()
        image.set_pixel_size(26)
        box.append(image)
        box.append(label)
        list_item.set_child(box)

    def _on_factory_widget_bind(self, factory, list_item):
        box = list_item.get_child()
        image = box.get_first_child()
        label = image.get_next_sibling()
        widget = list_item.get_item()
        image.set_from_file(widget.image)
        label.set_text(widget.name)


class RpmWheelApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = WheelRPMWindow(application=app)
        self.win.connect('destroy', self.quit)
        self.win.present()


if __name__ == "__main__":
    app = RpmWheelApp(application_id=APPLICATION_ID)
    app.run(sys.argv)

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

from games.autodetect import detect_running_game
from games.registry import GAMES, GAME_INDEX_BY_KEY
from installers.assetto_wrapper_installer import install_acc_wrapper, install_acr_wrapper
from installers.assetto_wrapper_installer import acc_wrapper_status as query_acc_wrapper_status
from installers.assetto_wrapper_installer import acr_wrapper_status as query_acr_wrapper_status
from installers.assetto_wrapper_installer import GAME_MISSING, WRAPPER_INSTALLED
from installers.ts_plugin_installer import install_ets2_plugins, install_ats_plugins
from installers.ts_plugin_installer import ets2_plugin_status as query_ets2_plugin_status
from installers.ts_plugin_installer import ats_plugin_status as query_ats_plugin_status
from installers.ts_plugin_installer import GAME_MISSING, PLUGIN_INSTALLED
from wheels.base import BaseWheel
from wheels.detect import find_wheel_with_failures, PERMISSION_HINT
from wheels.hid_backend import HidBackendUnavailable

APP_DIR = Path(__file__).resolve().parent
ICONS_DIR = APP_DIR / "icons"
APPLICATION_ID = "io.github.IvanVojtko.LogitechRpmIndicator"

MIN_MAX_RPM = 1000
MAX_MAX_RPM = 20000
RECONNECT_DELAY_SECONDS = 1.0
THREAD_JOIN_TIMEOUT_SECONDS = 2.0
RECONNECT_INACTIVITY_SECONDS = 3.0
AUTO_DETECT_INTERVAL_SECONDS = 1.0
DEFAULT_REMEMBER_LAST_GAME = False
DEFAULT_LAST_SELECTED_GAME = "ams_2"
SHIFT_LIGHT_THRESHOLD_COUNT = 5

MESSAGE_ERROR = "error"
MESSAGE_WARNING = "warning"
MESSAGE_SUCCESS = "success"
MESSAGE_SEVERITIES = (MESSAGE_ERROR, MESSAGE_WARNING, MESSAGE_SUCCESS)
MESSAGE_ICONS = {
    MESSAGE_ERROR: "dialog-error-symbolic",
    MESSAGE_WARNING: "dialog-warning-symbolic",
    MESSAGE_SUCCESS: "emblem-ok-symbolic",
}
MESSAGE_TAG_WHEEL = "wheel"
MESSAGE_TAG_TELEMETRY = "telemetry"


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

/* The bar tints its background per severity but leaves the label in the theme
   foreground colour, so it stays readable in both light and dark themes. */
.message-bar {
  border-radius: 12px;
  border: 1px solid alpha(@theme_fg_color, 0.10);
  padding: 10px 12px;
  background-color: alpha(@theme_fg_color, 0.08);
}

.message-bar.error {
  background-color: alpha(#e4534d, 0.18);
  border-color: alpha(#e4534d, 0.45);
}

.message-bar.warning {
  background-color: alpha(#b26a00, 0.18);
  border-color: alpha(#b26a00, 0.45);
}

.message-bar.success {
  background-color: alpha(#2f8f46, 0.18);
  border-color: alpha(#2f8f46, 0.45);
}

.message-bar-icon.error {
  color: #e4534d;
}

.message-bar-icon.warning {
  color: #b26a00;
}

.message-bar-icon.success {
  color: #2f8f46;
}

.message-bar-text {
  font-weight: 600;
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


class GameItem(GObject.Object):
    """One dropdown entry: plain data, rendered by the window's list factory."""
    __gtype_name__ = 'GameItem'

    def __init__(self, name: str, image_path: str):
        super().__init__()
        self._name = name
        self._image = image_path

    # The types matter: the dropdown search expression is only accepted by GTK
    # when the property it reads resolves to a string.
    @GObject.Property(type=str)
    def name(self) -> str:
        return self._name

    @GObject.Property(type=str)
    def image(self) -> str:
        return self._image


class WheelRPMWindow(Gtk.ApplicationWindow):
    _css_loaded = False

    def __init__(self, *args, **kwargs):
        # Create the main window
        super().__init__(*args, **kwargs)

        self.thread = None
        # Replaced per session by _start_telemetry; starts set so an
        # unexpected reader never mistakes it for a live session.
        self.stop_event = threading.Event()
        self.stop_event.set()
        self.running = False
        self.shared_rpm_percent = 0
        self.active_game = None
        self.auto_detect_enabled = False
        self.remember_last_selected_game = DEFAULT_REMEMBER_LAST_GAME
        self.last_selected_game_key = DEFAULT_LAST_SELECTED_GAME
        self.last_auto_detect_check = 0.0
        self.settings_path = self._get_settings_path()
        self.max_rpms = {game.key: game.default_max_rpm for game in GAMES if game.needs_max_rpm}
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

        self._build_message_bar(root)

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

        # Create a dropdown, one entry per GAMES entry and in the same order
        self.game_model = Gio.ListStore(item_type=GameItem)
        for game in GAMES:
            self.game_model.append(GameItem(name=game.label, image_path=icon_path(game.icon)))
        self.combo = Gtk.DropDown(model=self.game_model)
        self.combo.set_hexpand(True)
        # Search stays inert unless the dropdown is told how to turn an item
        # into text, so the expression has to be set alongside enable-search.
        self.combo.set_expression(Gtk.PropertyExpression.new(GameItem, None, "name"))
        self.combo.set_enable_search(True)
        if hasattr(self.combo, "set_search_match_mode"):
            # Prefix matching (the default) cannot find "Truck" in entries like
            # "Euro Truck Simulator 2 / American Truck Simulator".
            self.combo.set_search_match_mode(Gtk.StringFilterMatchMode.SUBSTRING)
        # Order matters: set_expression() swaps in GTK's built-in label-only
        # factory, so our icon factory has to be installed afterwards or every
        # game loses its icon.
        self.combo.set_factory(factory_widget)
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

        self.max_rpm_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.max_rpm_label = Gtk.Label(label="Max RPM")
        self.max_rpm_label.set_xalign(0)
        self.max_rpm_label.set_hexpand(True)
        self.max_rpm_input = Gtk.SpinButton.new_with_range(
            MIN_MAX_RPM, MAX_MAX_RPM, 100
        )
        self.max_rpm_input.set_numeric(True)
        self.max_rpm_input.connect("value-changed", self._on_max_rpm_changed)
        self.max_rpm_update_button = Gtk.Button(label="Update")
        self.max_rpm_update_button.connect("clicked", self._on_max_rpm_updated)
        self.max_rpm_row.append(self.max_rpm_label)
        self.max_rpm_row.append(self.max_rpm_input)
        self.max_rpm_row.append(self.max_rpm_update_button)
        self.max_rpm_row.set_visible(False)
        game_panel.append(self.max_rpm_row)

        self.ts_plugin_boxes = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.ts_plugin_boxes.set_homogeneous(True)
        self.ts_plugin_boxes.set_visible(False)
        game_panel.append(self.ts_plugin_boxes)

        ets2_plugin_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.ets2_plugin_button = Gtk.Button(label="Install ETS2 Telemetry Plugin")
        self.ets2_plugin_button.add_css_class("action-button")
        self.ets2_plugin_button.connect("clicked", self._on_ets2_plugin_install_clicked)
        self.ets2_plugin_status = Gtk.Label()
        self.ets2_plugin_status.set_xalign(0)
        self.ets2_plugin_status.set_wrap(True)
        ets2_plugin_box.append(self.ets2_plugin_button)
        ets2_plugin_box.append(self.ets2_plugin_status)
        self.ts_plugin_boxes.append(ets2_plugin_box)

        ats_plugin_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.ats_plugin_button = Gtk.Button(label="Install ATS Telemetry Plugin")
        self.ats_plugin_button.add_css_class("action-button")
        self.ats_plugin_button.connect("clicked", self._on_ats_plugin_install_clicked)
        self.ats_plugin_status = Gtk.Label()
        self.ats_plugin_status.set_xalign(0)
        self.ats_plugin_status.set_wrap(True)
        ats_plugin_box.append(self.ats_plugin_button)
        ats_plugin_box.append(self.ats_plugin_status)
        self.ts_plugin_boxes.append(ats_plugin_box)

        self.acc_wrapper_button = Gtk.Button(label="Install ACC Shared Memory wrapper")
        self.acc_wrapper_button.add_css_class("action-button")
        self.acc_wrapper_button.connect("clicked", self._on_acc_exe_install_clicked)
        self.acc_wrapper_status = Gtk.Label()
        self.acc_wrapper_status.set_xalign(0)
        self.acc_wrapper_status.set_wrap(True)
        self.acc_wrapper_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.acc_wrapper_box.set_visible(False)
        self.acc_wrapper_box.append(self.acc_wrapper_button)
        self.acc_wrapper_box.append(self.acc_wrapper_status)
        game_panel.append(self.acc_wrapper_box)

        self.acr_wrapper_button = Gtk.Button(label="Install ACR Shared Memory wrapper")
        self.acr_wrapper_button.add_css_class("action-button")
        self.acr_wrapper_button.connect("clicked", self._on_acr_exe_install_clicked)
        self.acr_wrapper_status = Gtk.Label()
        self.acr_wrapper_status.set_xalign(0)
        self.acr_wrapper_status.set_wrap(True)
        self.acr_wrapper_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.acr_wrapper_box.set_visible(False)
        self.acr_wrapper_box.append(self.acr_wrapper_button)
        self.acr_wrapper_box.append(self.acr_wrapper_status)
        game_panel.append(self.acr_wrapper_box)

        # Restore the saved selection only once every widget the handler touches
        # exists, otherwise "notify::selected" fires against a half-built window.
        if self.remember_last_selected_game:
            self.combo.set_selected(GAME_INDEX_BY_KEY[self.last_selected_game_key])
        self._on_game_selected_changed()

        # Detected further down, once the status widgets it reports into exist.
        self.wheel = None

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
        self.rescan_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self.rescan_button.add_css_class("flat")
        self.rescan_button.set_tooltip_text("Rescan for a connected wheel")
        self.rescan_button.set_valign(Gtk.Align.CENTER)
        self.rescan_button.connect("clicked", self._on_rescan_wheel_clicked)
        wheel_row.append(self.rescan_button)
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

        self._detect_wheel(announce_success=False)
        self._update_running_status()
        self._update_rpm_preview(0)
        self._on_game_selected_changed()
        GLib.timeout_add(80, self._refresh_process_state)
        self.connect("close-request", self._on_close_request)

    def _build_message_bar(self, root):
        self.message_revealer = Gtk.Revealer()
        self.message_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.message_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.message_bar.add_css_class("message-bar")
        self.message_icon = Gtk.Image()
        self.message_icon.add_css_class("message-bar-icon")
        self.message_text = Gtk.Label()
        self.message_text.add_css_class("message-bar-text")
        self.message_text.set_xalign(0)
        self.message_text.set_wrap(True)
        self.message_text.set_hexpand(True)
        dismiss_button = Gtk.Button.new_from_icon_name("window-close-symbolic")
        dismiss_button.add_css_class("flat")
        dismiss_button.set_tooltip_text("Dismiss this message")
        dismiss_button.set_valign(Gtk.Align.CENTER)
        dismiss_button.connect("clicked", self._on_message_dismissed)
        self.message_bar.append(self.message_icon)
        self.message_bar.append(self.message_text)
        self.message_bar.append(dismiss_button)
        self.message_revealer.set_child(self.message_bar)
        self._current_message = None
        self._current_message_tag = None
        root.append(self.message_revealer)

    def _show_message(self, text, severity=MESSAGE_ERROR, tag=None):
        """Reveal the message bar. Repeats of the current message are ignored.

        The telemetry loop retries once a second, so an unfiltered failure
        message would rebuild the bar continuously while a game is closed.
        """
        self._current_message_tag = tag
        if self._current_message == (text, severity):
            return
        self._current_message = (text, severity)
        for known_severity in MESSAGE_SEVERITIES:
            self.message_bar.remove_css_class(known_severity)
            self.message_icon.remove_css_class(known_severity)
        self.message_bar.add_css_class(severity)
        self.message_icon.add_css_class(severity)
        self.message_icon.set_from_icon_name(MESSAGE_ICONS[severity])
        self.message_text.set_text(text)
        self.message_revealer.set_reveal_child(True)

    def _clear_message(self, tag=None):
        """Hide the bar. With a tag, only a message from that source is hidden.

        Telemetry reconnecting must not wipe an unrelated warning such as a
        missing wheel, so it only clears what it put there itself.
        """
        if tag is not None and self._current_message_tag != tag:
            return
        self._current_message = None
        self._current_message_tag = None
        self.message_revealer.set_reveal_child(False)

    def _post_message(self, text, severity=MESSAGE_ERROR, tag=None):
        """Show a message from the telemetry thread, on the GTK main loop."""
        GLib.idle_add(self._show_message, text, severity, tag)

    def _post_clear_message(self, tag=None):
        GLib.idle_add(self._clear_message, tag)

    def _on_message_dismissed(self, _button):
        # Deliberately keeps _current_message: the telemetry loop retries every
        # second, and forgetting it would pop the same message back instantly.
        self.message_revealer.set_reveal_child(False)

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

    def _selected_game(self):
        selected = self.combo.get_selected()
        if selected == Gtk.INVALID_LIST_POSITION or selected >= len(GAMES):
            return None
        return GAMES[selected]

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

    @staticmethod
    def _parse_last_selected_game(raw_value):
        raw_value = raw_value.strip()
        if raw_value in GAME_INDEX_BY_KEY:
            return raw_value
        # Older versions saved the dropdown position instead. Read it against
        # the current list, which is what the last of them wrote it for.
        if raw_value.isdigit() and int(raw_value) < len(GAMES):
            return GAMES[int(raw_value)].key
        return DEFAULT_LAST_SELECTED_GAME

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
            self.last_selected_game_key = self._parse_last_selected_game(
                parser.get("general", "last_selected_game", fallback=DEFAULT_LAST_SELECTED_GAME)
            )
            for game in GAMES:
                if game.needs_max_rpm:
                    max_rpm = parser.getint(game.key, "max_rpm", fallback=game.default_max_rpm)
                    self.max_rpms[game.key] = max(MIN_MAX_RPM, min(max_rpm, MAX_MAX_RPM))
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
            "last_selected_game": self.last_selected_game_key,
        }
        for game_key, max_rpm in self.max_rpms.items():
            parser[game_key] = {"max_rpm": str(int(max_rpm))}
        parser["shift_lights"] = {
            "thresholds": self._serialize_shift_light_thresholds(self.shift_light_thresholds)
        }
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            with self.settings_path.open("w", encoding="utf-8") as settings_file:
                parser.write(settings_file)
        except Exception as exc:
            print(f"Failed to write settings: {exc}")

    def _read_and_save_max_rpm(self):
        game = self._selected_game()
        if game is not None and game.needs_max_rpm:
            self.max_rpms[game.key] = int(self.max_rpm_input.get_value())

        self._save_settings()

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

    def _on_max_rpm_changed(self, _spin):
        self._read_and_save_max_rpm()

    def _on_max_rpm_updated(self, _spin):
        if self.running:
            self._stop_telemetry()
            self._start_telemetry(self._selected_game())

    def _on_auto_detect_toggled(self, _checkbox):
        self.auto_detect_enabled = self.auto_detect_checkbox.get_active()
        self.last_auto_detect_check = 0.0
        self._save_settings()

    def _on_remember_last_game_toggled(self, _checkbox):
        self.remember_last_selected_game = self.remember_last_game_checkbox.get_active()
        game = self._selected_game()
        if game is not None:
            self.last_selected_game_key = game.key
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

    def _detect_wheel(self, announce_success):
        """(Re)scan for a wheel and report the outcome in the message bar."""
        # A scan supersedes whatever is on the bar -- including a message the
        # user dismissed -- so its result always gets announced.
        self._clear_message()
        if self.wheel:
            # The old handle has to go first or re-opening the same device fails.
            self.wheel.close()
            self.wheel = None

        try:
            self.wheel, failures = find_wheel_with_failures()
        except HidBackendUnavailable as error:
            self._update_wheel_status()
            self._show_message(
                f"No wheel can be detected because the HID backend failed to load: {error}",
                MESSAGE_ERROR,
                MESSAGE_TAG_WHEEL,
            )
            return
        self._update_wheel_status()

        if self.wheel:
            if announce_success:
                self._show_message("Wheel detected.", MESSAGE_SUCCESS, MESSAGE_TAG_WHEEL)
            return

        if failures:
            name, product_id, error = failures[0]
            self._show_message(
                f"{name} ({hex(product_id)}) was found but could not be opened: {error} "
                f"{PERMISSION_HINT}",
                MESSAGE_ERROR,
                MESSAGE_TAG_WHEEL,
            )
            return

        self._show_message(
            "No supported Logitech wheel found. Connect one and press Rescan; "
            "the RPM preview below works without hardware.",
            MESSAGE_WARNING,
            MESSAGE_TAG_WHEEL,
        )

    def _on_rescan_wheel_clicked(self, _button):
        # Rescanning swaps self.wheel, but a running telemetry thread holds the
        # old instance, so the button stays disabled while a session is live.
        if self.running:
            return
        self._detect_wheel(announce_success=True)

    def _on_game_selected_changed(self, *_args):
        game = self._selected_game()
        game_key = game.key if game is not None else None

        showing_max_rpm = game is not None and game.needs_max_rpm
        if showing_max_rpm:
            self.max_rpm_label.set_text(game.max_rpm_label)
            self.max_rpm_input.set_value(self.max_rpms[game.key])
        self.max_rpm_row.set_visible(showing_max_rpm)

        showing_ts_plugins = game_key == "truck_simulator"
        self.ts_plugin_boxes.set_visible(showing_ts_plugins)
        if showing_ts_plugins:
            self._refresh_ts_plugin_statuses()

        showing_acc_install = game_key == "assetto_corsa_competizione"
        self.acc_wrapper_box.set_visible(showing_acc_install)
        if showing_acc_install:
            self._refresh_acc_wrapper_status()

        showing_acr_install = game_key == "assetto_corsa_rally"
        self.acr_wrapper_box.set_visible(showing_acr_install)
        if showing_acr_install:
            self._refresh_acr_wrapper_status()

        if game is not None:
            self.last_selected_game_key = game.key
            if self.remember_last_selected_game:
                self._save_settings()

    @staticmethod
    def _set_install_status(label, message, css_class=None):
        label.remove_css_class("success-label")
        label.remove_css_class("warning-label")
        if css_class:
            label.add_css_class(css_class)
        label.set_text(message)

    def _refresh_plugin_status(self, label, status_query, game_name, short_name, is_wrapper = False):
        """Show whether the plugin, or wrapper, is already installed, before anything is clicked."""
        try:
            state, installed_paths = status_query()
        except Exception as exc:
            self._set_install_status(label, f"Could not check the {'wrapper' if is_wrapper else 'plugin'}: {exc}",
                "warning-label")
            return

        if state == GAME_MISSING:
            self._set_install_status(
                label, f"{game_name} was not found in your Steam libraries.", "warning-label"
            )
            return
        if (not is_wrapper):
            if state == PLUGIN_INSTALLED:
                self._set_install_status(
                    label, f"Plugin installed ({len(installed_paths)} file(s)).", "success-label"
                )
                return
            self._set_install_status(label, f"Plugin not installed for {short_name} yet.") 
        else:
            if state == WRAPPER_INSTALLED:
                self._set_install_status(
                    label, f"Wrapper executable is installed.", "success-label"
                )
                return
            self._set_install_status(label, f"Wrapper not installed for {short_name} yet.")

    def _refresh_ts_plugin_statuses(self):
        self._refresh_plugin_status(
            self.ets2_plugin_status, query_ets2_plugin_status, "Euro Truck Simulator 2", "ETS2"
        )
        self._refresh_plugin_status(
            self.ats_plugin_status, query_ats_plugin_status, "American Truck Simulator", "ATS"
        )

    def _refresh_acc_wrapper_status(self):
        self._refresh_plugin_status(
            self.acc_wrapper_status, query_acc_wrapper_status, "Assetto Corsa Competizione", "ACC", True
        )

    def _refresh_acr_wrapper_status(self):
        self._refresh_plugin_status(
            self.acr_wrapper_status, query_acr_wrapper_status, "Assetto Corsa Rally", "ACR", True
        )

    def _install_files(self, button, label, installer, short_name, is_wrapper = False):
        button.set_sensitive(False)
        try:
            installed_paths = installer(app_dir=Path(__file__).resolve().parent)
            if not installed_paths:
                self._set_install_status(
                    label, f"No {short_name} {'wrapper' if is_wrapper else 'plugin'} files were installed.",
                    "warning-label"
                )
                return
            self._set_install_status(
                label,
                f"Installed {len(installed_paths)} {short_name} {'wrapper' if is_wrapper else 'plugin'} file(s). "
                f"Restart {short_name} if it is already running.",
                "success-label",
            )
        except Exception as exc:
            self._set_install_status(label, str(exc), "warning-label")
        finally:
            button.set_sensitive(True)

    def _on_ets2_plugin_install_clicked(self, _button):
        self._install_files(
            self.ets2_plugin_button, self.ets2_plugin_status, install_ets2_plugins, "ETS2"
        )

    def _on_ats_plugin_install_clicked(self, _button):
        self._install_files(
            self.ats_plugin_button, self.ats_plugin_status, install_ats_plugins, "ATS"
        )

    def _on_acc_exe_install_clicked(self, _button):
        self._install_files(
            self.acc_wrapper_button, self.acc_wrapper_status, install_acc_wrapper, "ACC", True
        )

    def _on_acr_exe_install_clicked(self, _button):
        self._install_files(
            self.acr_wrapper_button, self.acr_wrapper_status, install_acr_wrapper, "ACR", True
        )

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
        self.rescan_button.set_sensitive(not self.running)
        self.rescan_button.set_tooltip_text(
            "Stop telemetry before rescanning" if self.running
            else "Rescan for a connected wheel"
        )
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
            self.active_game = None
            self._update_running_status()
            self.shared_rpm_percent = 0
        self._run_auto_detect_cycle()
        display_percent = self.shared_rpm_percent if self.running else 0
        self._update_rpm_preview(display_percent)
        return True

    def _stop_telemetry(self):
        # The flag is deliberately left set: this session owns it, and a new
        # session gets a fresh one. Clearing it here would hand a thread that
        # outlived the join a cleared flag and let it run forever.
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=THREAD_JOIN_TIMEOUT_SECONDS)
            if self.thread.is_alive():
                # Blocking reads have their own timeouts, so it will exit shortly
                # on its own; it just cannot be waited for any longer here.
                print("Telemetry thread did not stop in time; it will exit on its own.")
        if self.wheel:
            try:
                self.wheel.leds_rpm(0)
            except Exception as exc:
                # Runs on the GTK thread, including from close-request and the
                # auto-detect tick, so a dead wheel must not escape from here.
                print(f"Could not clear the wheel LEDs: {exc}")
        self.shared_rpm_percent = 0
        self._update_rpm_preview(0)
        self._clear_message(MESSAGE_TAG_TELEMETRY)
        self.thread = None
        self.active_game = None
        self.running = False

    def _on_close_request(self, _window):
        self._read_and_save_max_rpm()
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

    def _create_game(self, game):
        # max_rpms already holds the input's value: every change is stored as
        # it is made, and selecting a game loads its own value into the input.
        if game.needs_max_rpm:
            return game.create(max_rpm=self.max_rpms[game.key])
        return game.create()

    def _start_telemetry(self, game):
        if game is None:
            print("No game selected.")
            self._show_message("No game selected.", MESSAGE_ERROR, MESSAGE_TAG_TELEMETRY)
            return False
        telemetry_source = self._create_game(game)

        self.running = True
        # A fresh event per session. Reusing one would resurrect a thread that
        # was still shutting down when the previous session was stopped.
        stop_event = threading.Event()
        self.stop_event = stop_event
        self.shared_rpm_percent = 0
        self.active_game = game
        self.thread = threading.Thread(
            target=self.game_handling_loop,
            args=(telemetry_source, self.wheel, game.uses_shared_memory, stop_event),
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

        detected_index = GAME_INDEX_BY_KEY.get(detect_running_game())
        if detected_index is None:
            if self.running and self.active_game is not None:
                self._stop_telemetry()
                self._update_running_status()
            return
        detected_game = GAMES[detected_index]

        if self.combo.get_selected() != detected_index:
            self.combo.set_selected(detected_index)

        if not self.running:
            self._start_telemetry(detected_game)
            return

        if self.active_game is not detected_game:
            self._stop_telemetry()
            self._update_running_status()
            self._start_telemetry(detected_game)

    def on_button_clicked(self, _button):
        if self.running and (self.thread is None or not self.thread.is_alive()):
            self.running = False
            self.thread = None
            self.active_game = None
            self._update_running_status()
            self.shared_rpm_percent = 0
            self._update_rpm_preview(0)

        if not self.running:
            self._start_telemetry(self._selected_game())
        else:
            self._stop_telemetry()
            self._update_running_status()

    def game_handling_loop(self, game, wheel, uses_shared_memory, stop_event):
        if game is None:
            return

        udp_socket = None
        shared_memory_opened = False
        percent = 0
        last_send = 0.0
        last_packet_time = 0.0
        next_reconnect_time = 0.0
        while not stop_event.is_set():
            now = time.monotonic()

            # Shared memory games
            if uses_shared_memory:
                if shared_memory_opened is False:
                    if now < next_reconnect_time:
                        time.sleep(0.05)
                        continue
                    try:
                        game.connect()
                        shared_memory_opened = True
                        last_packet_time = time.monotonic()
                        self.shared_rpm_percent = 0
                        percent = 0
                        print("Telemetry memory location(s) opened.")
                        self._post_clear_message(MESSAGE_TAG_TELEMETRY)
                    except Exception as exc:
                        next_reconnect_time = now + RECONNECT_DELAY_SECONDS
                        self._handle_telemetry_connect_failure(game, exc)
                        continue

                try:
                    data = game.read_data()
                except Exception as exc:
                    self._handle_telemetry_read_failure(exc)
                    shared_memory_opened = WheelRPMWindow._close_game_shared_memory(game, shared_memory_opened)
                    next_reconnect_time = time.monotonic() + RECONNECT_DELAY_SECONDS
                    continue
            # UDP packets games
            else:
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
                        self._post_clear_message(MESSAGE_TAG_TELEMETRY)
                    except Exception as exc:
                        next_reconnect_time = now + RECONNECT_DELAY_SECONDS
                        self._handle_telemetry_connect_failure(game, exc)
                        continue

                try:
                    data = game.read_data(udp_socket=udp_socket)
                except socket.timeout:
                    if (time.monotonic() - last_packet_time >= RECONNECT_INACTIVITY_SECONDS):
                        udp_socket = WheelRPMWindow._close_game_socket(game, udp_socket)
                        next_reconnect_time = time.monotonic() + RECONNECT_DELAY_SECONDS
                    continue
                except Exception as exc:
                    self._handle_telemetry_read_failure(exc)
                    udp_socket = self._close_game_socket(game, udp_socket)
                    next_reconnect_time = time.monotonic() + RECONNECT_DELAY_SECONDS
                    continue

            last_packet_time = time.monotonic()
            try:
                percent = game.get_rpm_percent(data, percent)
            except Exception as exc:
                print(f"Telemetry parse failed, ignoring packet/data: {exc}")
                continue
            clamped_percent = max(0, min(int(percent), 100))
            self.shared_rpm_percent = clamped_percent
            now = time.perf_counter()
            if now - last_send >= 0.05:
                if wheel:
                    try:
                        wheel.leds_rpm(clamped_percent if clamped_percent != 0 else 0)
                    except Exception as exc:
                        # A wheel unplugged mid-session must not take the session
                        # with it: drop it and keep feeding the on-screen preview.
                        self._handle_wheel_write_failure(exc)
                        wheel = None
                last_send = now
            # Avoid using too much CPU for no reason
            if uses_shared_memory:
                time.sleep(0.05)

        self.shared_rpm_percent = 0
        try:
            if wheel:
                wheel.leds_rpm(0)
        except Exception:
            pass
        WheelRPMWindow._close_game_shared_memory(game, shared_memory_opened)
        WheelRPMWindow._close_game_socket(game, udp_socket)

    def _handle_telemetry_connect_failure(self, game, exc):
        print(f"Telemetry connect failed: {exc}")
        self._post_message(
            f"Waiting for telemetry from {game.__class__.__name__}: {exc}",
            MESSAGE_WARNING,
            MESSAGE_TAG_TELEMETRY,
        )
        self.shared_rpm_percent = 0
        time.sleep(0.05)

    def _handle_wheel_write_failure(self, exc):
        print(f"Wheel write failed, dropping the wheel for this session: {exc}")
        self._post_message(
            f"Lost contact with the wheel: {exc} "
            "Stop telemetry and press Rescan once it is reconnected.",
            MESSAGE_ERROR,
            MESSAGE_TAG_WHEEL,
        )

    def _handle_telemetry_read_failure(self, exc):
        print(f"Telemetry read failed, reopening shared memory: {exc}")
        self._post_message(
            f"Telemetry read failed, reconnecting: {exc}",
            MESSAGE_WARNING,
            MESSAGE_TAG_TELEMETRY,
        )

    @staticmethod
    def _close_game_shared_memory(game, shared_memory_opened):
        if not shared_memory_opened:
            return False
        try:
            disconnect = getattr(game, "disconnect", None)
            if callable(disconnect):
                disconnect()
        except Exception:
            pass
        return False

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
        item = list_item.get_item()
        image.set_from_file(item.image)
        label.set_text(item.name)


class RpmWheelApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.win = None
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        # Launching the app again only activates this running instance. A second
        # window would open the wheel again and fight over the telemetry port.
        if self.win is not None:
            self.win.present()
            return
        self.win = WheelRPMWindow(application=app)
        self.win.connect('destroy', self.quit)
        self.win.present()


if __name__ == "__main__":
    app = RpmWheelApp(application_id=APPLICATION_ID)
    app.run(sys.argv)

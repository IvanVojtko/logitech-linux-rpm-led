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
from games.assetto_corsa_shared_memory import AssettoCorsaSharedMemory
from games.outgauge import OutGauge
from games.truck_simulator import TruckSimulator
from games.wreckfest_2 import Wreckfest2
from games.autodetect import detect_running_game
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

APP_DIR = Path(__file__).resolve().parent
ICONS_DIR = APP_DIR / "icons"
APPLICATION_ID = "io.github.IvanVojtko.LogitechRpmIndicator"

AMS_2 =                         0
ASSETTO_CORSA =                 1
ASSETTO_CORSA_COMPETIZIONE =    2
ASSETTO_CORSA_RALLY =           3
BEAMNG =                        4
DIRT_RALLY_2_0 =                5
TRUCK_SIMULATOR =               6
F1_2019 =                       7
F1_2020 =                       8
F1_2022 =                       9
F1_2023 =                       10
FORZA_HORIZON_5 =               11
FORZA_HORIZON_6 =               12
LIVE_FOR_SPEED =                13
WRECKFEST_2 =                   14

DEFAULT_ASSETTO_MAX_RPM = 9000
DEFAULT_ASSETTO_RALLY_MAX_RPM = 6700
DEFAULT_BEAMNG_MAX_RPM = 6200
DEFAULT_LIVE_FOR_SPEED_MAX_RPM = 8000
MIN_MAX_RPM = 1000
MAX_MAX_RPM = 20000
RECONNECT_DELAY_SECONDS = 1.0
RECONNECT_INACTIVITY_SECONDS = 3.0
AUTO_DETECT_INTERVAL_SECONDS = 1.0
DEFAULT_REMEMBER_LAST_GAME = False
DEFAULT_LAST_SELECTED_GAME = AMS_2
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

GAME_KEY_TO_CHOICE = {
    "ams_2": AMS_2,
    "assetto_corsa": ASSETTO_CORSA,
    "assetto_corsa_competizione": ASSETTO_CORSA_COMPETIZIONE,
    "assetto_corsa_rally": ASSETTO_CORSA_RALLY,
    "beamng": BEAMNG,
    "dirt_rally_2_0": DIRT_RALLY_2_0,
    "truck_simulator": TRUCK_SIMULATOR,
    "f1_2019": F1_2019,
    "f1_2020": F1_2020,
    "f1_2022": F1_2022,
    "f1_2023": F1_2023,
    "forza_horizon_5": FORZA_HORIZON_5,
    "forza_horizon_6": FORZA_HORIZON_6,
    "live_for_speed": LIVE_FOR_SPEED,
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


class Widget(Gtk.Box):
    __gtype_name__ = 'Widget'

    def __init__(self, name: str, image_path: str):
        super().__init__()
        self._name = name

        # Create an image widget
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
        self.assetto_rally_max_rpm = DEFAULT_ASSETTO_RALLY_MAX_RPM
        self.beamng_max_rpm = DEFAULT_BEAMNG_MAX_RPM
        self.live_for_speed_max_rpm = DEFAULT_LIVE_FOR_SPEED_MAX_RPM
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

        # Create a dropdown (Gtk.ComboBoxText)
        self.model_widget = Gio.ListStore(item_type=Widget)
        self.model_widget.append(Widget(name="AMS 2 / pCars / pCars2", image_path=icon_path("ams-2.png")))
        self.model_widget.append(Widget(name="Assetto Corsa", image_path=icon_path("assetto.png")))
        self.model_widget.append(Widget(name="Assetto Corsa Competizione", image_path=icon_path("assetto-corsa-competizione.png")))
        self.model_widget.append(Widget(name="Assetto Corsa Rally", image_path=icon_path("assetto-corsa-rally.png")))
        self.model_widget.append(Widget(name="BeamNG", image_path=icon_path("beamng.png")))
        self.model_widget.append(Widget(name="Dirt Rally 2.0", image_path=icon_path("dirt-rally-2-0.png")))
        self.model_widget.append(Widget(name="Euro Truck Simulator 2 / American Truck Simulator",
            image_path=icon_path("euro-truck-simulator-2.png")))
        self.model_widget.append(Widget(name="F1 2019", image_path=icon_path("f1-2019.png")))
        self.model_widget.append(Widget(name="F1 2020", image_path=icon_path("f1-2020.png")))
        self.model_widget.append(Widget(name="F1 2022", image_path=icon_path("f1-2022.png")))
        self.model_widget.append(Widget(name="F1 2023", image_path=icon_path("f1-2023.png")))
        self.model_widget.append(Widget(name="Forza Horizon 5", image_path=icon_path("forza-horizon-5.png")))
        self.model_widget.append(Widget(name="Forza Horizon 6", image_path=icon_path("forza-horizon-6.png")))
        self.model_widget.append(Widget(name="Live for Speed", image_path=icon_path("live-for-speed.png")))
        self.model_widget.append(Widget(name="Wreckfest 2", image_path=icon_path("wreckfest-2.png")))
        self.combo = Gtk.DropDown(model=self.model_widget)
        self.combo.set_hexpand(True)
        # Search stays inert unless the dropdown is told how to turn an item
        # into text, so the expression has to be set alongside enable-search.
        self.combo.set_expression(Gtk.PropertyExpression.new(Widget, None, "name"))
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
        if self.remember_last_selected_game and self._is_valid_choice(self.last_selected_game_choice):
            self.combo.set_selected(self.last_selected_game_choice)
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
            value_assetto_max_rpm = parser.getint(
                "assetto_corsa", "max_rpm", fallback=DEFAULT_ASSETTO_MAX_RPM
            )
            value_assetto_rally_max_rpm = parser.getint(
                "assetto_corsa_rally", "max_rpm", fallback=DEFAULT_ASSETTO_RALLY_MAX_RPM
            )
            value_beamng_max_rpm = parser.getint(
                "beamng", "max_rpm", fallback=DEFAULT_BEAMNG_MAX_RPM
            )
            value_live_for_speed_max_rpm = parser.getint(
                "live_for_speed", "max_rpm", fallback=DEFAULT_LIVE_FOR_SPEED_MAX_RPM
            )
            self.assetto_max_rpm = max(MIN_MAX_RPM, min(value_assetto_max_rpm, MAX_MAX_RPM))
            self.assetto_rally_max_rpm = max(MIN_MAX_RPM, min(value_assetto_rally_max_rpm, MAX_MAX_RPM))
            self.beamng_max_rpm = max(MIN_MAX_RPM, min(value_beamng_max_rpm, MAX_MAX_RPM))
            self.live_for_speed_max_rpm = max(MIN_MAX_RPM, min(value_live_for_speed_max_rpm, MAX_MAX_RPM))
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
        parser["assetto_corsa_rally"] = {"max_rpm": str(int(self.assetto_rally_max_rpm))}
        parser["beamng"] = {"max_rpm": str(int(self.beamng_max_rpm))}
        parser["live_for_speed"] = {"max_rpm": str(int(self.live_for_speed_max_rpm))}
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
        selected_choice = self.combo.get_selected()
        if selected_choice == ASSETTO_CORSA:
            self.assetto_max_rpm = int(self.max_rpm_input.get_value())
        if selected_choice == ASSETTO_CORSA_RALLY:
            self.assetto_rally_max_rpm = int(self.max_rpm_input.get_value())
        elif selected_choice == BEAMNG:
            self.beamng_max_rpm = int(self.max_rpm_input.get_value())
        elif selected_choice == LIVE_FOR_SPEED:
            self.live_for_speed_max_rpm = int(self.max_rpm_input.get_value())

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
        selected_choice = self.combo.get_selected()

        if self.running:
            self._stop_telemetry()
            self._start_telemetry_for_choice(selected_choice)

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

    def _detect_wheel(self, announce_success):
        """(Re)scan for a wheel and report the outcome in the message bar."""
        # A scan supersedes whatever is on the bar -- including a message the
        # user dismissed -- so its result always gets announced.
        self._clear_message()
        if self.wheel:
            # The old handle has to go first or re-opening the same device fails.
            self.wheel.close()
            self.wheel = None

        self.wheel, failures = find_wheel_with_failures()
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
        selected_choice = self.combo.get_selected()

        if selected_choice == ASSETTO_CORSA:
            self.max_rpm_label.set_text("Assetto Max RPM")
            self.max_rpm_input.set_value(self.assetto_max_rpm)
        if selected_choice == ASSETTO_CORSA_RALLY:
            self.max_rpm_label.set_text("Assetto Rally Max RPM")
            self.max_rpm_input.set_value(self.assetto_rally_max_rpm)
        elif selected_choice == BEAMNG:
            self.max_rpm_label.set_text("BeamNG Max RPM")
            self.max_rpm_input.set_value(self.beamng_max_rpm)
        elif selected_choice == LIVE_FOR_SPEED:
            self.max_rpm_label.set_text("Live for Speed Max RPM")
            self.max_rpm_input.set_value(self.live_for_speed_max_rpm)

        self.max_rpm_row.set_visible(
            selected_choice == ASSETTO_CORSA or selected_choice == ASSETTO_CORSA_RALLY or selected_choice == BEAMNG
            or selected_choice == LIVE_FOR_SPEED)

        showing_ts_plugins = selected_choice == TRUCK_SIMULATOR
        self.ts_plugin_boxes.set_visible(showing_ts_plugins)
        if showing_ts_plugins:
            self._refresh_ts_plugin_statuses()
        
        showing_acc_install = selected_choice == ASSETTO_CORSA_COMPETIZIONE
        self.acc_wrapper_box.set_visible(showing_acc_install)
        if showing_acc_install:
            self._refresh_acc_wrapper_status()

        showing_acr_install = selected_choice == ASSETTO_CORSA_RALLY
        self.acr_wrapper_box.set_visible(showing_acr_install)
        if showing_acr_install:
            self._refresh_acr_wrapper_status()

        if self._is_valid_choice(selected_choice):
            self.last_selected_game_choice = int(selected_choice)
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
        self._clear_message(MESSAGE_TAG_TELEMETRY)
        self.thread = None
        self.active_game_choice = None
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
            self.assetto_max_rpm = int(self.max_rpm_input.get_value())
            self._save_settings()
            return AssettoCorsa(max_rpm=self.assetto_max_rpm)
        if choice == ASSETTO_CORSA_COMPETIZIONE:
            return AssettoCorsaSharedMemory()
        if choice == ASSETTO_CORSA_RALLY:
            self.assetto_rally_max_rpm = int(self.max_rpm_input.get_value())
            self._save_settings()
            return AssettoCorsaSharedMemory(max_rpm=self.assetto_rally_max_rpm)
        if choice == BEAMNG:
            self.beamng_max_rpm = int(self.max_rpm_input.get_value())
            self._save_settings()
            return OutGauge(max_rpm=self.beamng_max_rpm)
        if choice == LIVE_FOR_SPEED:
            self.live_for_speed_max_rpm = int(self.max_rpm_input.get_value())
            self._save_settings()
            return OutGauge(max_rpm=self.live_for_speed_max_rpm)
        if choice == TRUCK_SIMULATOR:
            return TruckSimulator()
        if choice == WRECKFEST_2:
            return Wreckfest2()
        return None

    def _start_telemetry_for_choice(self, choice):
        game = self._create_game_from_choice(choice)
        if game is None:
            print("No game selected.")
            self._show_message("No game selected.", MESSAGE_ERROR, MESSAGE_TAG_TELEMETRY)
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
        shared_memory_opened = False
        percent = 0
        last_send = 0.0
        last_packet_time = 0.0
        next_reconnect_time = 0.0
        while not self.stop_event.is_set():
            now = time.monotonic()

            # Shared memory games
            if choice == ASSETTO_CORSA_COMPETIZIONE or choice == ASSETTO_CORSA_RALLY:
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
                if choice in (FORZA_HORIZON_5, FORZA_HORIZON_6):
                    max_rpm, current_rpm = game.parse_rpm(data=data)
                    percent = game.get_rpm_percent(max_rpm=max_rpm, current_rpm=current_rpm)
                else:
                    percent = game.get_rpm_percent(data, percent)
            except Exception as exc:
                print(f"Telemetry parse failed, ignoring packet/data: {exc}")
                continue
            clamped_percent = max(0, min(int(percent), 100))
            self.shared_rpm_percent = clamped_percent
            now = time.perf_counter()
            if now - last_send >= 0.05:
                if wheel:
                    wheel.leds_rpm(clamped_percent if clamped_percent != 0 else 0)
                last_send = now
            # Avoid using too much CPU for no reason
            if choice == ASSETTO_CORSA_COMPETIZIONE or choice == ASSETTO_CORSA_RALLY:
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

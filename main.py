import sys
import time
import socket

import gi
import threading
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject, Gdk, GLib

from games.forza_horizon import ForzaHorizon5
from games.f12019 import F12019
from games.f12020 import F12020
from games.f12022 import F12022
from games.f12023 import F12023
from games.dirt_rally_2_0 import DirtRally2
from games.automobilista_2 import Automobilista2
from wheels.detect import find_wheel

FORZA_HORIZON_5 =   0
F1_2019 =           1
F1_2020 =           2
F1_2022 =           3
F1_2023 =           4
DIRT_RALLY_2_0 =    5
AMS_2 =             6

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

        self._ensure_css()
        self.add_css_class("rpm-window")
        self.set_title("G29 RPM LED indicator")
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
        self.model_widget.append(Widget(name="Forza Horizon 5", image_path='icons/forza-horizon-5.png'))
        self.model_widget.append(Widget(name="F1 2019", image_path='icons/f1-2019.png'))
        self.model_widget.append(Widget(name="F1 2020", image_path='icons/f1-2020.png'))
        self.model_widget.append(Widget(name="F1 2022", image_path='icons/f1-2022.png'))
        self.model_widget.append(Widget(name="F1 2023", image_path='icons/f1-2023.png'))
        self.model_widget.append(Widget(name="Dirt Rally 2.0", image_path='icons/dirt-rally-2-0.png'))
        self.model_widget.append(Widget(name="AMS 2 / pCars / pCars2", image_path='icons/ams-2.png'))
        self.combo = Gtk.DropDown(model=self.model_widget, factory=factory_widget)
        self.combo.set_hexpand(True)
        self.combo.set_enable_search(True)
        game_panel.append(self.combo)

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

    def _update_wheel_status(self):
        if self.wheel:
            self.wheel_status_icon.set_from_icon_name("emblem-ok-symbolic")
            self.wheel_status_text.set_text("Detected")
            return
        self.wheel_status_icon.set_from_icon_name("dialog-warning-symbolic")
        self.wheel_status_text.set_text("Not detected (preview only)")

    @staticmethod
    def _percent_to_led_bits(percent):
        return (
            0b11111 if percent > 84
            else 0b01111 if percent > 69
            else 0b00111 if percent > 39
            else 0b00011 if percent > 19
            else 0b00001 if percent > 4
            else 0
        )

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
            self._update_running_status()
            self.shared_rpm_percent = 0
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
        self.running = False

    def _on_close_request(self, _window):
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

    def on_button_clicked(self, _button):
        if self.running and (self.thread is None or not self.thread.is_alive()):
            self.running = False
            self.thread = None
            self._update_running_status()
            self.shared_rpm_percent = 0
            self._update_rpm_preview(0)

        choice = self.combo.get_selected()
        if choice == FORZA_HORIZON_5:
            game = ForzaHorizon5()
        elif choice == F1_2019:
            game = F12019()
        elif choice == F1_2020:
            game = F12020()
        elif choice == F1_2022:
            game = F12022()
        elif choice == F1_2023:
            game = F12023()
        elif choice == DIRT_RALLY_2_0:
            game = DirtRally2()
        elif choice == AMS_2:
            game = Automobilista2()
        else:
            game = None

        if game is None:
            print("No game selected.")
            return

        if not self.running:
            self.running = True
            self.stop_event.clear()
            self.shared_rpm_percent = 0
            self.thread = threading.Thread(
                target=self.game_handling_loop,
                args=(game, self.wheel, choice),
                daemon=True,
            )
            self.thread.start()
            self._update_running_status()
        else:
            self._stop_telemetry()
            self._update_running_status()

    def game_handling_loop(self, game, wheel, choice):
        if game is None:
            return

        udp_socket = None
        percent = 0
        last_send = 0.0
        try:
            udp_socket = game.connect()
            udp_socket.settimeout(0.2)
            while not self.stop_event.is_set():
                try:
                    data = game.read_data(udp_socket=udp_socket)
                except socket.timeout:
                    continue
                if choice == FORZA_HORIZON_5:
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
        except Exception as exc:
            print(f"Telemetry loop stopped: {exc}")
        finally:
            self.shared_rpm_percent = 0
            try:
                if wheel:
                    wheel.leds_rpm(0)
            except Exception:
                pass
            if udp_socket:
                udp_socket.close()

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
    app = RpmWheelApp(application_id="com.example.GtkApplication")
    app.run(sys.argv)

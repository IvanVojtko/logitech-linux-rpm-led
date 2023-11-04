import sys
import gi
import multiprocessing
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject

from games.forza_horizon import ForzaHorizon5
from games.f12019 import F12019
from games.f12023 import F12023
from games.dirt_rally_2_0 import DirtRally2
from wheels.g29 import G29

FORZA_HORIZON_5 = 0
F1_2019 = 1
F1_2023 = 2
DIRT_RALLY_2_0 = 3


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
    def __init__(self, *args, **kwargs):
        # Create the main window
        super().__init__(*args, **kwargs)

        self.thread = None
        self.running = False

        self.set_title("G29 RPM LED indicator")
        self.set_default_size(250, 100)
        # Create a box to organize the elements
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        inner_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        title = Gtk.Label()
        title.set_text("Select your game:")
        box.append(title)
        box.append(inner_box)
        self.set_child(box)

        # Create factory
        factory_widget = Gtk.SignalListItemFactory()
        factory_widget.connect("setup", self._on_factory_widget_setup)
        factory_widget.connect("bind", self._on_factory_widget_bind)

        # Create a dropdown (Gtk.ComboBoxText)
        self.model_widget = Gio.ListStore(item_type=Widget)
        self.model_widget.append(Widget(name="Forza Horizon 5", image_path='icons/forza-horizon-5.png'))
        self.model_widget.append(Widget(name="F1 2019", image_path='icons/f1-2019.png'))
        self.model_widget.append(Widget(name="F1 2023", image_path='icons/f1-2023.png'))
        self.model_widget.append(Widget(name="Dirt Rally 2.0", image_path='icons/dirt-rally-2-0.png'))
        combo = Gtk.DropDown(model=self.model_widget, factory=factory_widget)
        inner_box.append(combo)

        self.wheel = G29()
        connected = self.wheel.connect()

        wheel_check = Gtk.CheckButton()
        wheel_check.set_sensitive(False)
        wheel_check.set_label("Wheel detected?")
        if not connected:
            wheel_check.set_active(False)
        else:
            wheel_check.set_active(True)

        # Create a button (Gtk.Button)
        button = Gtk.Button(label="Start")
        button.connect("clicked", self.on_button_clicked, combo)
        inner_box.append(button)
        box.append(wheel_check)

    def on_button_clicked(self, button, combo):
        choice = combo.get_selected()
        if choice == FORZA_HORIZON_5:
            game = ForzaHorizon5()
        elif choice == F1_2019:
            game = F12019()
        elif choice == F1_2023:
            game = F12023()
        elif choice == DIRT_RALLY_2_0:
            game = DirtRally2()
        else:
            game = None

        if not self.running:
            self.running = True
            self.thread = multiprocessing.Process(target=self.game_handling_loop, args=(game, self.wheel, choice))
            self.thread.daemon = True
            self.thread.start()
            button.set_label("Stop")
        else:
            self.thread.terminate()
            self.running = False
            button.set_label("Start")

    def game_handling_loop(self, game, wheel, choice):
        udp_socket = game.connect()
        percent = 0

        while True:
            data = game.read_data(udp_socket=udp_socket)
            if choice == FORZA_HORIZON_5:
                max_rpm, current_rpm = game.parse_rpm(data=data)
                percent = game.get_rpm_percent(max_rpm=max_rpm, current_rpm=current_rpm)
            else:
                percent = game.get_rpm_percent(data, percent)
            if percent != 0:
                wheel.leds_rpm(percent)
            else:
                wheel.leds_rpm(0)

    def _on_factory_widget_setup(self, factory, list_item):
        box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label()
        image = Gtk.Image()
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

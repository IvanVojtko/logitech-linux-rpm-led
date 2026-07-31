import unittest

try:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Gtk, Gio, GObject

    import main

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False


@unittest.skipUnless(GTK_AVAILABLE, "GTK 4 / libadwaita bindings are not available")
class DropDownSearchTest(unittest.TestCase):
    """The dropdown search only works when Widget.name resolves to a string.

    A bare @GObject.Property yields PyObject, which GTK rejects, leaving the
    search box accepting keystrokes without ever filtering the list.
    """

    def _build_store(self):
        store = Gio.ListStore(item_type=main.Widget)
        for name in ("Assetto Corsa", "Euro Truck Simulator 2 / American Truck Simulator", "Wreckfest 2"):
            store.append(main.Widget(name=name, image_path="icon.png"))
        return store

    def test_name_property_is_a_string(self) -> None:
        self.assertEqual(main.Widget.find_property("name").value_type, GObject.TYPE_STRING)

    def test_dropdown_accepts_the_search_expression(self) -> None:
        dropdown = Gtk.DropDown(model=self._build_store())
        dropdown.set_expression(Gtk.PropertyExpression.new(main.Widget, None, "name"))
        self.assertIsNotNone(dropdown.get_expression())

    def test_expression_filters_the_game_list(self) -> None:
        string_filter = Gtk.StringFilter(
            expression=Gtk.PropertyExpression.new(main.Widget, None, "name")
        )
        string_filter.set_match_mode(Gtk.StringFilterMatchMode.SUBSTRING)
        string_filter.set_ignore_case(True)
        string_filter.set_search("truck")
        model = Gtk.FilterListModel(model=self._build_store(), filter=string_filter)

        matches = [model.get_item(index).name for index in range(model.get_n_items())]
        self.assertEqual(matches, ["Euro Truck Simulator 2 / American Truck Simulator"])


@unittest.skipUnless(GTK_AVAILABLE, "GTK 4 / libadwaita bindings are not available")
class DropDownFactoryOrderTest(unittest.TestCase):
    """Enabling search must not cost the games their icons.

    Gtk.DropDown.set_expression() installs GTK's own label-only factory, which
    silently replaces a factory that was set earlier -- the icons then vanish
    from both the button and the popup list.
    """

    def _configure(self, dropdown, factory, factory_first):
        expression = Gtk.PropertyExpression.new(main.Widget, None, "name")
        if factory_first:
            dropdown.set_factory(factory)
            dropdown.set_expression(expression)
        else:
            dropdown.set_expression(expression)
            dropdown.set_factory(factory)
        dropdown.set_enable_search(True)

    def test_expression_set_after_the_factory_discards_it(self) -> None:
        factory = Gtk.SignalListItemFactory()
        dropdown = Gtk.DropDown()
        self._configure(dropdown, factory, factory_first=True)
        self.assertIsNot(dropdown.get_factory(), factory)

    def test_factory_set_after_the_expression_survives(self) -> None:
        factory = Gtk.SignalListItemFactory()
        dropdown = Gtk.DropDown()
        self._configure(dropdown, factory, factory_first=False)
        self.assertIs(dropdown.get_factory(), factory)
        self.assertIsNotNone(dropdown.get_expression())


if __name__ == "__main__":
    unittest.main()

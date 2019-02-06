
import os
from threading import Thread

from bibed.constants import BIBED_DATA_DIR
from bibed.gui.helpers import widget_properties
from bibed.gui.gtk import Gtk


class BibedSplashWindow(Gtk.Window):

    def __init__(self):
        # Gtk.WindowType.TOPLEVEL
        super().__init__()

        # Set position and decoration
        self.set_position(Gtk.WindowPosition.CENTER)
        # self.set_decorated(False)
        self.set_default_size(300, 200)

        # Add box and label
        self.box = widget_properties(
            Gtk.Box(),
            classes=['splash-screen'],
        )

        self.add(self.box)

        self.icon = Gtk.Image.new_from_file(
            os.path.join(BIBED_DATA_DIR, 'images', 'logo.png')
        )

        self.lbl = Gtk.Label()
        self.lbl.set_markup('<big>Bibed\nLoading…</big>')

        self.box.pack_start(self.icon, False, False, 0)
        self.box.pack_start(self.lbl, True, True, 0)


class BibedSplash(Thread):

    def __init__(self):
        super().__init__()

        # Create a popup window
        self.window = BibedSplashWindow()

    def run(self):
        # Show the splash screen without causing startup notification
        # https://developer.gnome.org/gtk3/stable/GtkWindow.html#gtk-window-set-auto-startup-notification
        self.window.set_auto_startup_notification(False)
        self.window.show_all()
        self.window.set_auto_startup_notification(True)

        self.window.show()
        self.window.present()

        # Need to call Gtk.main to draw all widgets
        while Gtk.events_pending():
            Gtk.main_iteration()

    def destroy(self):
        while Gtk.events_pending():
            Gtk.main_iteration()
        self.window.destroy()

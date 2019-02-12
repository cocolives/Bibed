
import os
from threading import Thread

from bibed.constants import BIBED_DATA_DIR
from bibed.gui.helpers import add_classes
from bibed.gtk import Gtk


class BibedSplashWindow(Gtk.Window):

    def __init__(self):
        # Gtk.WindowType.TOPLEVEL
        super().__init__()

        # Set position and decoration
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_decorated(False)
        self.set_default_size(300, 150)

        add_classes(self, ['splash-screen'])

        self.button = Gtk.Button()

        self.inbox = Gtk.Box()

        self.icon = Gtk.Image.new_from_file(
            os.path.join(BIBED_DATA_DIR, 'images', 'logo.png')
        )

        self.lbl = Gtk.Label()
        self.lbl.set_markup('<big>Bibed\nLoading…</big>')

        self.inbox.pack_start(self.icon, False, False, 0)
        self.inbox.pack_start(self.lbl, True, True, 0)

        self.button.add(self.inbox)

        self.add(self.button)


def start_splash():

    window = BibedSplashWindow()

    window.set_auto_startup_notification(False)

    window.show_all()
    window.show()
    window.present()

    # Need to call Gtk.main to draw all widgets.
    # See app.BibEdApplication.do_command_line() too.
    # 20190212: both are needed for splash to show.
    while Gtk.events_pending():
        Gtk.main_iteration()

    window.set_auto_startup_notification(True)

    return window

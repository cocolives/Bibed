
import os

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
        self.set_keep_above(True)
        self.set_default_size(300, 150)

        add_classes(self, ['splash-screen'])

        self.button = Gtk.Button()

        self.inbox = Gtk.Box()

        self.icon = Gtk.Image.new_from_file(
            os.path.join(BIBED_DATA_DIR, 'images', 'scalable', 'logo.svg')
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

    # Need to call Gtk.main to draw all widgets. Need to block on events too,
    # else main window appears before splash shows up. Sometimes splash never
    # shows up, sometimes it does. 35 events is the base number of events
    # needed for splash to be up on screen, with CSS loaded and applied.
    # NOTE: the “while Gtk.events_pending(): Gtk.main_iteration()” loop
    # is not sufficient. Waiting 40 events is too much, this makes app
    # loading freeze if the use doesn't click anywhere.
    for i in range(35):
        Gtk.main_iteration_do(True)

    window.set_auto_startup_notification(True)

    return window

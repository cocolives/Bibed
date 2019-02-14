
from bibed.gtk import Gtk, Gdk
from bibed.constants import (
    GRID_BORDER_WIDTH,
    GRID_COLS_SPACING,
    GRID_ROWS_SPACING,
)
from bibed.gui.css import GtkCssAwareMixin
from bibed.gui.helpers import add_classes, widget_properties


class BibedSplashWindow(Gtk.Window, GtkCssAwareMixin):

    def __init__(self):
        # Gtk.WindowType.TOPLEVEL
        super().__init__()

        # Set position and decoration
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_default_size(300, 150)
        self.set_type_hint(Gdk.WindowTypeHint.SPLASHSCREEN)
        self.set_urgency_hint(True)

        add_classes(self, ['splash-screen'])

        self.button = Gtk.Button()
        self.button.connect('clicked', self.hide_splash)

        self.ingrid = Gtk.Grid()
        self.ingrid.set_border_width(GRID_BORDER_WIDTH)
        self.ingrid.set_column_spacing(GRID_COLS_SPACING)
        self.ingrid.set_row_spacing(GRID_ROWS_SPACING)
        self.ingrid.set_column_homogeneous(False)
        self.ingrid.set_row_homogeneous(False)

        self.setup_resources_and_css()

        pixcon = self.icon_theme.load_icon('bibed-logo', 256, 0)
        self.icon = Gtk.Image.new_from_pixbuf(pixcon)

        self.lbl = Gtk.Label(xalign=0.5)
        self.lbl.set_markup('<span size="32768"><b>Bibed</b></span>\nBibliographic Assistant')

        self.status_box = Gtk.HBox()

        self.status = Gtk.Label(xalign=0.0)
        self.status.set_markup('Loading…')

        self.spinner = widget_properties(
            Gtk.Spinner(),
            expand=False,
            halign=Gtk.Align.END,
            valign=Gtk.Align.CENTER,
        )
        self.spinner.start()

        # Grid.attach(widget, left, top, width, height)
        self.ingrid.attach(self.icon, 0, 0, 1, 1)
        self.ingrid.attach(self.lbl, 1, 0, 1, 1)

        self.status_box.pack_start(self.status, True, True, 0)
        self.status_box.pack_start(self.spinner, False, False, 0)
        self.ingrid.attach(self.status_box, 0, 1, 2, 1)

        self.button.add(self.ingrid)

        self.add(self.button)

    def set_transient_for(self, parent):

        super().set_transient_for(parent)
        self.spin()

    def set_status(self, message):

        self.status.set_markup(message)

        self.spin()

    def spin(self):

        while Gtk.events_pending():
            Gtk.main_iteration()

    def hide_splash(self, *args):

        self.hide()


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


from bibed.constants import (
    GRID_COLS_SPACING,
    GRID_ROWS_SPACING,
    GRID_BORDER_WIDTH,
    BOXES_BORDER_WIDTH,
)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk, Gdk, Pango  # NOQA


def label_with_markup(text):

    label = Gtk.Label()
    label.set_markup(text)
    label.set_xalign(0.0)

    return label


def grid_with_common_params():

    grid = Gtk.Grid()
    grid.set_border_width(GRID_BORDER_WIDTH)
    grid.set_column_spacing(GRID_COLS_SPACING)
    grid.set_row_spacing(GRID_ROWS_SPACING)
    # grid.set_column_homogeneous(True)
    # grid.set_row_homogeneous(True)
    return grid


def vbox_with_icon_and_label(icon_name, label_text):

    label_box = Gtk.VBox()
    label_box.set_border_width(BOXES_BORDER_WIDTH)

    label_box.pack_start(
        Gtk.Image.new_from_icon_name(
            icon_name,
            Gtk.IconSize.DIALOG
        ), False, False, 0
    )
    label_box.pack_start(Gtk.Label(label_text), True, True, 0)
    label_box.set_size_request(100, 100)
    label_box.show_all()

    return label_box

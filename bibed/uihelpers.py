
from bibed.constants import (
    GRID_COLS_SPACING,
    GRID_ROWS_SPACING,
    GRID_BORDER_WIDTH,
    BOXES_BORDER_WIDTH,
)

from bibed.gtk import Gtk, Gdk


# ————————————————————————————————————————————————————————————— Functions


def notification_callback(notification, action_name):
    # Unused as of 20190119.

    # Use in conjunction with:
    #    def do_notification(self, message):
    #
    #        notification = Notify.Notification.new('Bibed', message)
    #        notification.set_timeout(Notify.EXPIRES_NEVER)
    #        notification.add_action('quit', 'Quit',
    #                                notification_callback)
    #        notification.show()

    notification.close()


def label_with_markup(text, xalign=None, yalign=None):

    if xalign is None:
        xalign = 0.0

    if yalign is None:
        yalign = 0.5

    label = Gtk.Label()
    label.set_markup(text)
    label.set_xalign(xalign)
    label.set_yalign(yalign)

    return label


def grid_with_common_params():

    grid = Gtk.Grid()
    grid.set_border_width(GRID_BORDER_WIDTH)
    grid.set_column_spacing(GRID_COLS_SPACING)
    grid.set_row_spacing(GRID_ROWS_SPACING)
    # grid.set_column_homogeneous(True)
    # grid.set_row_homogeneous(True)
    return grid


def widget_expand_align(widget, expand=False, halign=None, valign=None):

    if halign is None:
        halign = Gtk.Align.START

    if valign is None:
        valign = Gtk.Align.CENTER

    widget.props.expand = expand
    widget.props.halign = halign
    widget.props.valign = valign

    return widget


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

import os

from bibed.constants import (
    GRID_COLS_SPACING,
    GRID_ROWS_SPACING,
    GRID_BORDER_WIDTH,
    BOXES_BORDER_WIDTH,
    GENERIC_HELP_SYMBOL,
)

from bibed.gui.gtk import Gtk, Gdk


# ——————————————————————————————————————————————————————————————————— Functions


def get_screen_resolution():

    if os.name != 'posix':
        import ctypes
        user32 = ctypes.windll.user32

        user32.SetProcessDPIAware()

        screensize = (
            user32.GetSystemMetrics(0),
            user32.GetSystemMetrics(1)
        )

        # Multi-monitor setup.
        # screensize = user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)

    else:
        Gdk.Display.get_primary_monitor()

    return screensize


def mp(name, var=None):

    if var is None:
        print('\t{}'.format(name))
    else:
        print('\t{}: {}'.format(name, var))


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


def grid_with_common_params(column_homogeneous=False, row_homogeneous=False):

    grid = Gtk.Grid()
    grid.set_border_width(GRID_BORDER_WIDTH)
    grid.set_column_spacing(GRID_COLS_SPACING)
    grid.set_row_spacing(GRID_ROWS_SPACING)
    # grid.set_column_homogeneous(True)
    # grid.set_row_homogeneous(True)
    return grid


def debug_widget(widget):

    print('\t{0}'.format(widget))
    print('\texpand={0}'.format(widget.props.expand))
    print('\thexpand={0}/{1}'.format(widget.props.hexpand,
                                     widget.props.hexpand_set))
    print('\tvexpand={0}/{1}'.format(widget.props.vexpand,
                                     widget.props.vexpand_set))
    print('\theight_request={0}'.format(widget.props.height_request))
    print('\twidth_request={0}'.format(widget.props.width_request))
    print('\thalign={0}'.format(widget.props.halign))
    print('\tvalign={0}'.format(widget.props.valign))
    print('\tmargin={0}'.format(widget.props.margin))
    print('\tmargin_top={0}'.format(widget.props.margin_top))
    print('\tmargin_bottom={0}'.format(widget.props.margin_bottom))
    print('\tmargin_left={0}'.format(widget.props.margin_left))
    print('\tmargin_right={0}'.format(widget.props.margin_right))
    print('\tmargin_start={0}'.format(widget.props.margin_start))
    print('\tmargin_end={0}'.format(widget.props.margin_end))


def widget_properties(widget, expand=False, halign=None, valign=None, margin=None, margin_top=None, margin_bottom=None, margin_left=None, margin_right=None, margin_start=None, margin_end=None, width=None, height=None, debug=False):

    if __debug__ and debug: mp('WIDGET', widget)

    if halign is not None:
        if __debug__ and debug: mp('halign', halign)
        widget.props.halign = halign

    if valign is not None:
        if __debug__ and debug: mp('valign', valign)
        widget.props.valign = valign

    if width is None:
        width = -1

    if height is None:
        height = -1

    if __debug__ and debug: mp('expand1', expand)

    if isinstance(expand, bool):
        if __debug__ and debug: mp('expand2', expand)
        widget.props.expand = expand

        if expand:
            if __debug__ and debug: mp('expand is True')
            widget.set_hexpand(True)
            widget.set_vexpand(True)
        else:
            if __debug__ and debug: mp('expand is False')
            widget.set_hexpand(False)
            widget.set_vexpand(False)
    else:
        if expand == Gtk.Orientation.VERTICAL:
            if __debug__ and debug: mp('expand horizontally')
            widget.set_vexpand(True)
            # widget.set_hexpand(False)

        else:
            if __debug__ and debug: mp('expand vertically')
            # Gtk.Orientation.VERTICAL
            widget.set_hexpand(True)
            # widget.set_vexpand(False)

    if margin is None:
        if margin_top is not None:
            widget.props.margin_top = margin_top

        if margin_bottom is not None:
            widget.props.margin_bottom = margin_bottom

        if margin_left is not None:
            widget.props.margin_left = margin_left

        if margin_right is not None:
            widget.props.margin_right = margin_right

        if margin_start is not None:
            widget.props.margin_start = margin_start

        if margin_end is not None:
            widget.props.margin_end = margin_end
    else:
        widget.props.margin = margin

    if width != -1 and height != -1:
        if __debug__ and debug: mp('width', width)
        if __debug__ and debug: mp('height', height)

        widget.set_size_request(width, height)

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


def flat_unclickable_button2(label_text, icon_name=None):

    if icon_name is None:
        button = Gtk.Button()
        button.set_label(label_text)

    else:
        button = Gtk.Button(icon_name)
        button.set_label(label_text)

    button.set_relief(Gtk.ReliefStyle.NONE)

    return widget_properties(
        button,
        expand=Gtk.Orientation.HORIZONTAL,
        halign=Gtk.Align.CENTER,
        valign=Gtk.Align.CENTER,
    )


def flat_unclickable_button_in_hbox(label_text, icon_name=None):

    label_with_icon = Gtk.HBox()
    label_with_icon.set_border_width(BOXES_BORDER_WIDTH)

    if icon_name is not None:
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
        label_with_icon.pack_start(icon, False, False, 0)

    label_with_icon.pack_start(Gtk.Label(label_text), False, False, 0)
    label_with_icon.set_size_request(100, 30)

    label_with_icon.show_all()

    return label_with_icon


def flat_unclickable_button_in_grid(label_text, icon_name=None):

    label_with_icon = Gtk.Grid()
    label_with_icon.set_border_width(BOXES_BORDER_WIDTH)

    label = Gtk.Label(label_text)
    label_with_icon.attach(label, 0, 0, 1, 1)

    if icon_name is not None:
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)

        label_with_icon.attach_next_to(
            icon,
            label,
            Gtk.PositionType.LEFT, 1, 1
        )

    label_with_icon.set_size_request(100, 30)

    label_with_icon.show_all()

    return label_with_icon


flat_unclickable_button = flat_unclickable_button_in_grid


def in_scrolled(widget, width=None, height=None):

    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_policy(
        Gtk.PolicyType.NEVER,
        Gtk.PolicyType.AUTOMATIC
    )

    widget_properties(
        widget,
        expand=True,
        halign=Gtk.Align.FILL,
        valign=Gtk.Align.FILL,
        width=width,
        height=height,
    )

    scrolled_window.add(widget)

    return scrolled_window


def scrolled_textview():

    sw = Gtk.ScrolledWindow()

    sw.set_policy(
        Gtk.PolicyType.NEVER,
        Gtk.PolicyType.AUTOMATIC
    )

    sw = widget_properties(
        sw,
        expand=True,
        halign=Gtk.Align.FILL,
        valign=Gtk.Align.FILL,
        width=600,
        height=400,
        # debug=True,
    )

    tv = widget_properties(
        Gtk.TextView(),
        expand=True,
        halign=Gtk.Align.FILL,
        valign=Gtk.Align.FILL,
        width=600,
        height=400,
        # debug=True,
    )

    # self.textview.get_buffer().set_text('Nothing yet here.')

    sw.add(tv)

    return sw, tv


def frame_defaults(title):

    frame = Gtk.Frame.new(title)
    frame.props.shadow_type = Gtk.ShadowType.IN
    frame.props.label_xalign = 0.1
    frame.props.label_yalign = 0.5

    return frame


def build_entry_field_labelled_entry(mnemonics, field_name, entry):

    field_node = getattr(mnemonics, field_name)

    if field_node is None:
        field_has_help = False
        field_label = field_name.title()
        field_help = ''

    else:
        field_has_help = field_node.doc is not None
        field_label = field_node.label
        field_help = field_node.doc

    lbl = widget_properties(
        Gtk.Label(),
        expand=False,
        margin=BOXES_BORDER_WIDTH,
        halign=Gtk.Align.START,
        valign=Gtk.Align.CENTER,
        width=50,
    )

    lbl.set_markup_with_mnemonic(
        '{label}{help}'.format(
            label=field_label,
            help=GENERIC_HELP_SYMBOL
            if field_has_help else ''))

    etr = widget_properties(
        Gtk.Entry(),
        expand=Gtk.Orientation.HORIZONTAL,
        # margin=BOXES_BORDER_WIDTH,
        halign=Gtk.Align.FILL,
        valign=Gtk.Align.CENTER,
        width=300,
    )

    etr.set_name(field_name)
    etr.set_text(entry.get_field(field_name, ''))

    lbl.set_mnemonic_widget(etr)

    if field_has_help:
        lbl.set_tooltip_markup(field_help)
        etr.set_tooltip_markup(field_help)

    return lbl, etr


def build_entry_field_textview(mnemonics, field_name, entry):

    field_node = getattr(mnemonics, field_name)

    if field_node is None:
        field_has_help = False
        # field_label = field_name.title()
        field_help = ''

    else:
        field_has_help = field_node.doc is not None
        # field_label = field_node.label
        field_help = field_node.doc

    scrolled, textview = scrolled_textview()

    textview.set_name(field_name)

    buffer = textview.get_buffer()
    buffer.set_text(entry.get_field(field_name, ''))

    # textview.connect(
    #   'changed', self.on_field_changed, field_name)

    if field_has_help:
        textview.set_tooltip_markup(field_help)

    return scrolled, textview

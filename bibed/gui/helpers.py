import os
import logging

from bibed.foundations import ldebug
from bibed.constants import (
    GRID_COLS_SPACING,
    GRID_ROWS_SPACING,
    GRID_BORDER_WIDTH,
    BOXES_BORDER_WIDTH,
    GENERIC_HELP_SYMBOL,
    HELP_POPOVER_LABEL_MARGIN,
)

from bibed.gui.gtk import Gtk, Gdk


LOGGER = logging.getLogger(__name__)

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


def get_children_recursive(start_node, reverse=True):
    ''' Get all children of :param:`start_node`, recursively.

        .. note:: this function will reverse results by default, probably
            because of a bug or a misunderstanding of myself at some point.

            For some reason, returning children “as is”, without reversing
            the list, gives results inversed of what I thought about.

            You can still get “as is” result by setting :param:`reverse`
            to `False`.

        .. versionadded:: 0.9-develop
    '''

    # assert ldebug('CONTAINER {}', start_node)

    # Get Bin before Container, else ScrolledWindow returns
    # the Viewport instead of the real child.

    children = []

    if isinstance(start_node, Gtk.Bin):
        child = start_node.get_child()
        # assert ldebug('YIELD {}', child)
        children.append(child)
        children.extend(get_children_recursive(child, reverse=False))

    elif isinstance(start_node, Gtk.Container):
        for child in start_node.get_children():
            # assert ldebug('YIELD {}', child)
            children.append(child)
            children.extend(get_children_recursive(child, reverse=False))

    if reverse:
        return reversed(children)

    return children


def find_child_by_name(start_node, widget_name):

    if start_node.get_name() == widget_name:
        return start_node

    if isinstance(start_node, Gtk.Container):
        for child in start_node.get_children():
            result = find_child_by_name(child, widget_name)

            if result:
                return result

    return None


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


def stack_switch_next(stack, reverse=False):
    ''' Switch to next or previous stack level, and return the one switched to. '''

    children = stack.get_children()

    first = children[0]
    last  = children[-1]

    if reverse:
        children = reversed(children)

    visible_child = stack.get_visible_child()
    # get_visible_child_name()[source]

    make_next_visible = False

    for child in children:
        if make_next_visible:
            stack.set_visible_child(child)
            return child

        if child == visible_child:
            if reverse and child == first:
                stack.set_visible_child(last)
                return last

            elif not reverse and child == last:
                stack.set_visible_child(first)
                return first
            else:
                make_next_visible = True


def label_with_markup(text, name=None, xalign=None, yalign=None, debug=None):

    label = Gtk.Label(name=name)
    label.set_markup(text)

    if xalign is not None:
        if __debug__ and debug: mp('xalign', xalign)  # NOQA
        label.set_xalign(xalign)

    if yalign is not None:
        if __debug__ and debug: mp('yalign', yalign)  # NOQA
        label.set_yalign(yalign)

    return label


def add_classes(widget, classes):

    style_context = widget.get_style_context()

    for class_name in classes:
        style_context.add_class(class_name)


def remove_classes(widget, classes):

    style_context = widget.get_style_context()

    for class_name in classes:
        style_context.remove_class(class_name)


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


def widget_properties(widget, expand=False, halign=None, valign=None, margin=None, margin_top=None, margin_bottom=None, margin_left=None, margin_right=None, margin_start=None, margin_end=None, width=None, height=None, classes=None, connect_to=None, connect_signal=None, connect_args=None, connect_kwargs=None, default=False, activates_default=False, no_show_all=False, debug=False):

    if __debug__ and debug: mp('WIDGET', widget)  # NOQA

    if halign is not None:
        if __debug__ and debug: mp('halign', halign)  # NOQA
        widget.props.halign = halign

    if valign is not None:
        if __debug__ and debug: mp('valign', valign)  # NOQA
        widget.props.valign = valign

    if classes is None:
        classes = []

    if width is None:
        width = -1

    if height is None:
        height = -1

    if isinstance(expand, bool):
        if __debug__ and debug: mp('expand', expand)  # NOQA
        widget.props.expand = expand

        if expand:
            # if __debug__ and debug: mp('expand is True')  # NOQA
            widget.set_hexpand(True)
            widget.set_vexpand(True)
        else:
            # if __debug__ and debug: mp('expand is False')  # NOQA
            widget.set_hexpand(False)
            widget.set_vexpand(False)
    else:
        if expand == Gtk.Orientation.VERTICAL:
            if __debug__ and debug: mp('expand horizontally')  # NOQA
            widget.set_vexpand(True)
            # widget.set_hexpand(False)

        else:
            if __debug__ and debug: mp('expand vertically')  # NOQA
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
        if __debug__ and debug: mp('width', width)  # NOQA
        if __debug__ and debug: mp('height', height)  # NOQA

        widget.set_size_request(width, height)

    if default:
        if __debug__ and debug: mp('SET default widget')  # NOQA

        if not widget.get_can_default():
            widget.set_can_default(True)

        widget.set_receives_default(True)

    if activates_default:
        if __debug__ and debug: mp('SET activate default')  # NOQA

        widget.set_activates_default(True)

    if classes:
        if __debug__ and debug: mp('classes', classes)  # NOQA

        style_context = widget.get_style_context()

        for class_name in classes:
            style_context.add_class(class_name)

    if connect_to is not None:
        if connect_args is None:
            connect_args = ()
        if connect_kwargs is None:
            connect_kwargs = {}

        if connect_signal is None:
            try:
                guessed_signal = connect_to.__name__.rsplit('_', 1)[1]

            except Exception:
                # This could be just a programming mistake during
                # development, let's get to assert call below.
                pass

            else:
                # Warning: this could still fail because false positive
                # like "value-changed" signal names.
                if guessed_signal in ('changed', 'clicked', 'hide', 'show', ):
                    connect_signal = guessed_signal

        assert(connect_signal is not None)

        if __debug__ and debug:
            mp('connect', connect_to.__name__)
            mp('args', connect_args)
            mp('kwargs', connect_kwargs)
        widget.connect(
            connect_signal, connect_to,
            *connect_args, **connect_kwargs)

    if no_show_all:
        if __debug__ and debug: mp('SET no_show_all')  # NOQA
        widget.set_no_show_all(True)

    return widget


def build_help_popover(attached_to, help_markup, position, onfocus_list):

    popover = Gtk.Popover()
    # vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    label = widget_properties(
        Gtk.Label(),
        margin=HELP_POPOVER_LABEL_MARGIN,
    )
    label.set_markup(help_markup)

    # vbox.pack_start(label, False, True, 10)

    # popover.add(vbox)
    popover.add(label)

    popover.set_position(position)
    popover.set_relative_to(attached_to)
    # popover.show_all()

    def show_popover(*args, **kwargs):
        # popover.popup()
        LOGGER.info('popover show')
        popover.show_all()
        popover.show()

    def hide_popover(*args, **kwargs):
        # popover.popdown()
        LOGGER.info('popover hide')
        popover.hide()

    # Avoid conflict between tooltip and popover.
    if attached_to.props.has_tooltip:
        attached_to.set_tooltip_markup(None)

    for widget in onfocus_list:
        widget.connect('focus-in-event', show_popover)
        widget.connect('focus-out-event', hide_popover)
        # widget.connect('motion-notify-event', show_popover)
        # widget.connect('leave-notify-event', hide_popover)
        pass

    return popover


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
    button.set_sensitive(False)

    return widget_properties(
        button,
        expand=False,
        halign=Gtk.Align.CENTER,
        valign=Gtk.Align.CENTER,
        margin=10,
    )


def flat_unclickable_label(label_text, icon_name=None):

    label = widget_properties(
        Gtk.Label(),
        expand=True,
        halign=Gtk.Align.CENTER,
        valign=Gtk.Align.CENTER,
    )
    label.set_markup('<b>{}</b>'.format(label_text))
    label.show_all()

    return label


def flat_unclickable_button_in_hbox(label_text, icon_name=None):

    label_with_icon = widget_properties(
        Gtk.HBox(),
        expand=True,
        halign=Gtk.Align.FILL,
        valign=Gtk.Align.FILL,
    )

    label_with_icon.set_border_width(BOXES_BORDER_WIDTH)

    if icon_name is not None:
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
        label_with_icon.pack_start(icon, False, False, 0)

    label_with_icon.pack_start(widget_properties(
        Gtk.Label(label_text),
        classes=['dnd-object'],
        # debug=True
    ), False, False, 0)
    
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


flat_unclickable_button = flat_unclickable_button_in_hbox


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

    tv.set_wrap_mode(Gtk.WrapMode.WORD)

    sw.add(tv)

    return sw, tv


def frame_defaults(title):

    frame = Gtk.Frame.new(title)
    frame.props.shadow_type = Gtk.ShadowType.IN
    frame.props.label_xalign = 0.1
    frame.props.label_yalign = 0.5

    return frame


def build_label_and_switch(lbl_text, swi_notify_func, swi_initial_state, func_args=None):

    if func_args is None:
        func_args = ()

    label = widget_properties(label_with_markup(
        lbl_text),
        expand=Gtk.Orientation.HORIZONTAL,
        halign=Gtk.Align.START,
        valign=Gtk.Align.CENTER,
    )

    switch = widget_properties(
        Gtk.Switch(),
        halign=Gtk.Align.START,
        valign=Gtk.Align.CENTER
    )

    switch.connect(
        'notify::active',
        swi_notify_func, *func_args)

    switch.set_active(swi_initial_state)

    return label, switch


def build_entry_field_labelled_entry(fields_docs, fields_labels, field_name, entry):

    if isinstance(fields_labels, str):
        field_label = fields_labels
    else:
        field_label = getattr(fields_labels, field_name)

    if isinstance(fields_docs, str):
        field_doc = fields_docs
    else:
        field_doc = getattr(field_doc, field_name)

    # TODO: remove these ldebug() calls
    # when every field is documented / labelled.

    if field_label is None:
        ldebug('\t>>> Field {} has no label', field_name)
    if field_doc is None:
        ldebug('\t>>> Field {} has no documentation', field_name)

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
            label=field_label if field_label else field_name.title(),
            help=GENERIC_HELP_SYMBOL
            if field_doc else ''))

    etr = widget_properties(
        Gtk.Entry(),
        expand=Gtk.Orientation.HORIZONTAL,
        # margin=BOXES_BORDER_WIDTH,
        halign=Gtk.Align.FILL,
        valign=Gtk.Align.CENTER,
        width=300,
    )

    etr.set_name(field_name)
    if entry is not None:
        etr.set_text(entry.get_field(field_name, ''))

    lbl.set_mnemonic_widget(etr)

    if field_doc:
        lbl.set_tooltip_markup(field_doc)
        etr.set_tooltip_markup(field_doc)

    return lbl, etr


def build_entry_field_textview(fields_docs, field_name, entry):

    scrolled, textview = scrolled_textview()

    textview.set_name(field_name)

    buffer = textview.get_buffer()
    buffer.set_text(entry.get_field(field_name, ''))

    # textview.connect(
    #   'changed', self.on_field_changed, field_name)

    field_help = getattr(fields_docs, field_name)

    if field_help:
        textview.set_tooltip_markup(field_help)

    return scrolled, textview

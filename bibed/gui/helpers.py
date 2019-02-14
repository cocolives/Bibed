import os
import logging

from bibed.ltrace import ldebug

from bibed.constants import (
    FileTypes,
    BIBED_DATA_DIR,
    BIBED_ICONS_DIR,
    GRID_COLS_SPACING,
    GRID_ROWS_SPACING,
    GRID_BORDER_WIDTH,
    BOXES_BORDER_WIDTH,
    GENERIC_HELP_SYMBOL,
    HELP_POPOVER_LABEL_MARGIN,
)

from bibed.preferences import preferences
from bibed.gtk import GLib, Gtk, Gdk, Gio


LOGGER = logging.getLogger(__name__)

# ——————————————————————————————————————————————————————————————————— Functions


def bibed_icon_name(icon_category, icon_name):

    return 'bibed-{}-{}'.format(icon_category, icon_name)


def is_dark_theme():

    '''
    	gint		textAvg, bgAvg;


	textAvg = style->text[GTK_STATE_NORMAL].red / 256 +
	        style->text[GTK_STATE_NORMAL].green / 256 +
	        style->text[GTK_STATE_NORMAL].blue / 256;


	bgAvg = style->bg[GTK_STATE_NORMAL].red / 256 +
	        style->bg[GTK_STATE_NORMAL].green / 256 +
	        style->bg[GTK_STATE_NORMAL].blue / 256;


	if (textAvg > bgAvg)
		darkTheme = TRUE;

        cf. https://lzone.de/blog/Detecting%20a%20Dark%20Theme%20in%20GTK

        We need to detect if automathemely is installed.
        https://www.linuxuprising.com/2018/08/automatically-switch-to-light-dark-gtk.html
    '''
    pass


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


def message_dialog(window, dialog_type, title, secondary_text, ok_callback, *args, **kwargs):

    # Gtk.MessageType.QUESTION

    dialog = Gtk.MessageDialog(
        window, 0, dialog_type,
        Gtk.ButtonsType.OK_CANCEL,
        title
    )
    dialog.format_secondary_markup(secondary_text)
    dialog.set_default_response(Gtk.ResponseType.OK)
    add_classes(
        dialog.get_widget_for_response(Gtk.ResponseType.OK),
        ['suggested-action'],
    )

    response = dialog.run()

    if response == Gtk.ResponseType.OK:
        ok_callback(*args, **kwargs)

    dialog.destroy()


def find_child_by_name(start_node, widget_name):

    if start_node.get_name() == widget_name:
        return start_node

    if isinstance(start_node, Gtk.Bin):
        result = find_child_by_name(start_node.get_child(), widget_name)

        if result:
            return result

    if isinstance(start_node, Gtk.Container):
        for child in start_node.get_children():
            result = find_child_by_name(child, widget_name)

            if result:
                return result

    return None


def find_child_by_class(start_node, widget_class):

    if isinstance(start_node, widget_class):
        return start_node

    if isinstance(start_node, Gtk.Bin):
        result = find_child_by_class(start_node.get_child(), widget_class)

        if result:
            return result

    if isinstance(start_node, Gtk.Container):
        for child in start_node.get_children():
            result = find_child_by_class(child, widget_class)

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


def label_with_markup(text, name=None, xalign=None, yalign=None, justify=None, ellipsize=None, line_wrap=False, debug=None):

    label = Gtk.Label(name=name)
    label.set_markup_with_mnemonic(text)

    if ellipsize is not None:
        if __debug__ and debug: mp('ellipsize', ellipsize)  # NOQA
        label.set_ellipsize(ellipsize)

    if justify is not None:
        if __debug__ and debug: mp('justify', justify)  # NOQA
        label.set_justify(justify)

    if line_wrap is not None:
        if __debug__ and debug: mp('line_wrap', line_wrap)  # NOQA
        label.set_line_wrap(line_wrap)

    if xalign is not None:
        if __debug__ and debug: mp('xalign', xalign)  # NOQA
        label.set_xalign(xalign)

    if yalign is not None:
        if __debug__ and debug: mp('yalign', yalign)  # NOQA
        label.set_yalign(yalign)

    return label


def markup_bib_filename(filename, filetype, with_folder=True, same_line=True, small_size=False, big_size=False, same_size=True, parenthesis=False, missing=False):

    assert filetype is not None
    assert not (small_size and big_size)

    # Get only the filename, not the extension.
    basename = os.path.basename(filename).rsplit('.', 1)[0]
    dirname  = os.path.dirname(filename)

    home_folder = os.path.expanduser('~')
    working_folder = preferences.working_folder

    if with_folder:
        if dirname == working_folder:
            folder = 'Working folder'

        elif dirname.startswith(working_folder):
            remaining = dirname[len(working_folder):]

            folder = '<i>Working folder</i> {remaining}'.format(
                remaining=remaining)

        elif dirname.startswith(home_folder):
            remaining = dirname[len(home_folder):]

            folder = '<i>Home directory</i> {remaining}'.format(
                remaining=remaining)

        else:
            folder = dirname

    else:
        folder = None

    if missing:
        # Notice the ending space.
        format_template = '<span color="red" size="{file_size}">missing file</span> '

    else:
        format_template = ''

    if filetype & FileTypes.USER:
        format_template += (
            '<span size="{file_size}"><b>{basename}</b></span>{separator}'
            + (
                '<span size="{folder_size}" color="grey">'
                '{par_left}in {folder}{par_right}</span>'
                if with_folder else ''
            )
        )

        format_kwargs = {
            'separator': ' ' if same_line else '\n',
            'basename': GLib.markup_escape_text(basename),
            'folder': GLib.markup_escape_text(folder),
        }

    else:
        # System files, or special entry (like “All”)…
        # No folder for them, anyway.
        # Thus, no need for separator.
        format_template += '{basename}'
        format_kwargs = {
            # No need to GLib.markup_escape_text(),
            # Bibed's filenames are ascii-proof.
            'basename': basename.title(),
        }

    if big_size:
        file_size = 'large'
        folder_size = 'small'

    elif small_size:
        file_size = 'small'
        folder_size = 'xx-small'

    else:
        file_size = 'medium'
        folder_size = 'x-small'

    if same_size:
        folder_size = file_size

    if parenthesis:
        format_kwargs.update({
            'par_left': '(',
            'par_right': ')',
        })

    else:
        format_kwargs.update({
            'par_left': '',
            'par_right': '',
        })

    format_kwargs.update({
        'file_size': file_size,
        'folder_size': folder_size,
    })

    return format_template.format(**format_kwargs)


def markup_entries(entries, count=None, max=None):
    '''
        :param count: then number of entries. Optional argument. In some
            contexts you already have it. Passing it will save a len() call.
            Otherwise, the function computes it.

        :param max: the max number of entries to display textually before
            counting others in the “and NNN other(s)” information. Must be
            between 2 and 10.
    '''

    if count is None:
        count = len(entries)

    if max is None:
        max = 10

    elif max < 2:
        max = 2

    if max > 10:
        max = 10

    if count > max:
        entries_list = '\n'.join(
            '  - {}'.format(entry.short_display)
            for entry in entries[:max]
        ) + '\nand {other} other(s).'.format(
            other=count - max
        )
    else:
        entries_list = '\n'.join(
            '  - {}'.format(entry.short_display)
            for entry in entries
        )

    return entries_list


def add_classes(widget, classes):

    style_context = widget.get_style_context()

    for class_name in classes:
        style_context.add_class(class_name)


def remove_classes(widget, classes):

    style_context = widget.get_style_context()

    for class_name in classes:
        style_context.remove_class(class_name)


def flash_field(field, number=None, interval=None):

    if number is None:
        number = 9

    if number % 2 == 0:
        # Be sure we don't let the field in error state…
        number += 1

    if interval is None:
        interval = 100

    def _flash_field_callback(field, interval, current, number):

        if current % 2 == 0:
            add_classes(field, ['error'])
        else:
            remove_classes(field, ['error'])

        if current < number:
            GLib.timeout_add(interval,
                             _flash_field_callback, field,
                             interval, current + 1, number)

        # stop the interval, we relaunched it already.
        return False

    GLib.timeout_add(interval,
                     _flash_field_callback, field,
                     interval, 0, number)


def grid_with_common_params(column_homogeneous=False, row_homogeneous=False):

    grid = Gtk.Grid()
    grid.set_border_width(GRID_BORDER_WIDTH)
    grid.set_column_spacing(GRID_COLS_SPACING)
    grid.set_row_spacing(GRID_ROWS_SPACING)

    if column_homogeneous:
        grid.set_column_homogeneous(True)

    if row_homogeneous:
        grid.set_row_homogeneous(True)

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


def widget_properties(widget, expand=False, halign=None, valign=None, margin=None, margin_top=None, margin_bottom=None, margin_left=None, margin_right=None, margin_start=None, margin_end=None, width=None, height=None, classes=None, connect_to=None, connect_signal=None, connect_args=None, connect_kwargs=None, default=False, activates_default=False, no_show_all=False, can_focus=None, debug=False):

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

    if can_focus is not None:
        if __debug__ and debug: mp('can_focus', can_focus)  # NOQA
        widget.set_can_focus(can_focus)

    if no_show_all:
        if __debug__ and debug: mp('SET no_show_all')  # NOQA
        widget.set_no_show_all(True)

    return widget


def widget_call_method(widgets, method_name, *args, **kwargs):

    for widget in widgets:
        getattr(widget, method_name)(*args, **kwargs)


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


def vbox_with_icon_and_label(name, label_markup, icon_name=None, icon_path=None, icon_size=None):

    assert icon_name is not None or icon_path is not None

    if icon_size is None:
        icon_size = Gtk.IconSize.DIALOG

    label_box = Gtk.VBox()
    label_box.set_name(name)
    label_box.set_border_width(BOXES_BORDER_WIDTH)

    if icon_name:
        gicon = Gio.ThemedIcon(name=icon_name)
        icon = Gtk.Image.new_from_gicon(gicon, icon_size)

    else:
        icon = Gtk.Image.new_from_file(
            icon_path
        )

    label = Gtk.Label()
    label.set_markup_with_mnemonic(label_markup)

    label_box.pack_start(icon, False, False, 0)
    label_box.pack_start(label, True, True, 0)
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


def flat_unclickable_button_in_hbox(name, label_markup, icon_name=None, icon_path=None, icon_size=None, classes=None):

    hbox = widget_properties(
        Gtk.HBox(),
        expand=False,
        halign=Gtk.Align.START,
        valign=Gtk.Align.CENTER,
        classes=classes,
    )

    hbox.set_name(name)

    hbox.set_border_width(BOXES_BORDER_WIDTH)

    if icon_size is None:
        icon_size = Gtk.IconSize.BUTTON

    if icon_name:
        gicon = Gio.ThemedIcon(name=icon_name)
        icon = Gtk.Image.new_from_gicon(gicon, icon_size)

    elif icon_path:
        icon = Gtk.Image.new_from_file(
            icon_path
        )

    hbox.pack_start(icon, False, False, 0)

    label = widget_properties(Gtk.Label(), margin_left=10)
    label.set_markup_with_mnemonic(label_markup)

    hbox.pack_start(widget_properties(
        label,
        expand=False,
        halign=Gtk.Align.CENTER,
        valign=Gtk.Align.CENTER,
        # debug=True
    ), False, False, 0)

    hbox.set_size_request(30, 30)

    hbox.show_all()

    return hbox


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

    # Set the switch before connecting the
    # signal, else this triggers the callback(s).
    switch.set_active(swi_initial_state)

    switch.connect(
        'notify::active',
        swi_notify_func, *func_args)

    return label, switch


def build_entry_field_labelled_entry(fields_docs, fields_labels, field_name, entry):

    if isinstance(fields_labels, str):
        field_label = fields_labels
    else:
        field_label = getattr(fields_labels, field_name)

    if isinstance(fields_docs, str):
        field_doc = fields_docs
    else:
        field_doc = getattr(fields_docs, field_name)

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


# ————————————————————————————————————————————————————————————————————— Classes

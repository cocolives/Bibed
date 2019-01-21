
from bibed.constants import (
    GRID_COLS_SPACING,
    GRID_ROWS_SPACING,
    GRID_BORDER_WIDTH,
    BOXES_BORDER_WIDTH,
)

from bibed.gtk import Gtk, Gdk

# ——————————————————————————————————————————————————————————————————— Functions


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


def widget_properties(widget, expand=False, halign=None, valign=None, margin=None, margin_top=None, margin_bottom=None, margin_left=None, margin_right=None, margin_start=None, margin_end=None):

    if halign is not None:
        widget.props.halign = halign

    if valign is not None:
        widget.props.valign = valign

    if type(expand) == type(bool):
        widget.props.expand = expand

        if expand:
            widget.set_hexpand(True)
            widget.set_vexpand(True)
        else:
            widget.set_hexpand(False)
            widget.set_vexpand(False)
    else:
        if expand == Gtk.Orientation.VERTICAL:
            widget.set_vexpand(True)
            # widget.set_hexpand(False)

        else:
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
            Gtk.PositionType.LEFT, 1, 1)

    label_with_icon.set_size_request(100, 30)

    label_with_icon.show_all()

    return label_with_icon


flat_unclickable_button = flat_unclickable_button_in_grid


def dnd_scrolled_flowbox(name=None, title=None, dialog=None):

    if title is None:
        title = name.title()

    frame = Gtk.Frame.new(title)
    frame.props.shadow_type = Gtk.ShadowType.IN
    frame.props.label_xalign = 0.1
    frame.props.label_yalign = 0.5

    scrolled = Gtk.ScrolledWindow()

    scrolled.set_policy(Gtk.PolicyType.NEVER,
                        Gtk.PolicyType.AUTOMATIC)

    # debug_widget(scrolled)

    flowbox = widget_properties(
        DnDFlowBox(name=name, dialog=dialog),
        expand=True,
    )

    # flowbox.set_valign(Gtk.Align.START)
    flowbox.set_max_children_per_line(3)
    flowbox.set_min_children_per_line(2)

    flowbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
    # flowbox.set_activate_on_single_click(False)

    scrolled.add(flowbox)
    frame.add(scrolled)

    # scrolled.set_size_request(100, 100)
    flowbox.set_size_request(100, 100)

    return frame, scrolled, flowbox


# ————————————————————————————————————————————————————————————————————— Classes


class DnDFlowBox(Gtk.FlowBox):

    def __init__(self, *args, **kwargs):

        self.dialog = kwargs.pop('dialog')

        super().__init__(*args, **kwargs)

        # Each is a drag-n-drop source
        self.drag_source_set(
            Gdk.ModifierType.BUTTON1_MASK, [],
            Gdk.DragAction.MOVE)
        self.drag_source_set_target_list(None)
        self.drag_source_add_text_targets()

        # And a drag-n-drop destination
        self.drag_dest_set(
            Gtk.DestDefaults.ALL, [],
            Gdk.DragAction.MOVE)
        self.drag_dest_set_target_list(None)
        self.drag_dest_add_text_targets()

        self.connect('drag-motion',
                     self.on_drag_motion)
        self.connect('drag-begin',
                     self.on_drag_begin)
        self.connect('drag-data-get',
                     self.on_drag_data_get)
        self.connect('drag-data-received',
                     self.on_drag_data_received)
        # self.connect('drag-data-delete',
        #              self.on_drag_data_delete)
        self.connect('drag-end',
                     self.on_drag_end)

        self.reset_drag_data()

    def reset_drag_data(self):

        self.is_drag_source = False
        self.drag_motion_origin = None
        self.drag_motion_destination = None
        self.drag_widgets_to_add = None

    def add_item(self, child_name, index=None):

        # This should change dynamically, given where the
        # child is when the drag begin.
        # dnd_area.drag_source_set_icon_name(Gtk.STOCK_GO_FORWARD)

        child = flat_unclickable_button(
            child_name,
            'orientation-portrait-symbolic')

        if index is None:
            # HEADS UP: index can be 0 (thus False)
            self.add(child)
        else:
            self.insert(child, index)

        # print('\t\tADD {}, {}'.format(child_name, index))

        # Necessary for add() after DnD operations,
        # because everything else is already shown.
        child.show_all()

    def add_items(self, children_names):

        for child_name in children_names:
            self.add_item(child_name)

    def remove_item(self, child_name):

        for child in self.get_children():
            if child.get_child().get_children()[1].get_text() == child_name:
                # Thils will remove it from the container.
                # Cf. https://lazka.github.io/pgi-docs/Gtk-3.0/classes/Container.html#Gtk.Container.remove  # NOQA
                child.destroy()
                # print('\t\tREMOVE {}'.format(child_name))

    def remove_items(self, child_names=None):

        for child in self.get_children():
            if child_names is None:
                child.destroy()

            else:
                child_name = child.get_child().get_children()[1].get_text()

                if child_name in child_names:
                    # destroy() will remove it from the container.
                    # Cf. https://lazka.github.io/pgi-docs/Gtk-3.0/classes/Container.html#Gtk.Container.remove  # NOQA
                    child.destroy()
                    # print('\t\tREMOVE {}'.format(child_name))

    def get_children_names(self):

        return [
            child.get_child().get_children()[1].get_text()
            for child in self.get_children()
        ]

    def get_index_of(self, child):

        for index in range(len(self.get_children())):
            if child == self.get_child_at_index(index):
                break

        return index

    def get_names_of_selected_or_drag_source(self):

        # Other things than the source selected ?
        selected = self.get_selected_children()

        names = set()

        if selected:
            names |= set([
                child.get_child().get_children()[1].get_text()
                for child in selected
            ])

        if self.drag_motion_origin:
            # Add the drag origin in case it
            # was not selected before dragging.
            # Sometimes it's None if the user dragged
            # too fast for the motion to detect it.
            hbox = self.drag_motion_origin.get_child()
            names |= set([hbox.get_children()[1].get_text()])

        return list(names)

    def on_drag_begin(self, *args, **kwargs):

        print('DRAG BEGIN in={}'.format(args[0].get_name()))

        # Make the container know it's the source of a drag,
        # to handle self-to-self drag-n-drop items reordering.
        self.is_drag_source = True

    def on_drag_motion(self, widget, drag_context, x, y, time):

        motion_source = widget.get_child_at_pos(x, y)

        if self.is_drag_source:
            # Don't record drag_motion_origin
            # on destination if it's a different
            # container from the drag_source,
            # this is non-sense and produces bugs.

            if self.drag_motion_origin is None:
                self.drag_motion_origin = motion_source

                try:
                    print('DRAG MOTION origin={}'.format(
                        motion_source.get_child().get_children(
                        )[1].get_text()))

                except AttributeError:
                    pass

        if motion_source == self.drag_motion_destination:
            # We already noted that.
            return True

        # Overwrite at each motion to get destination (moving target).
        self.drag_motion_destination = motion_source

        if motion_source is None:
            print('DRAG MOTION destination=<empty area> of {}'.format(
                widget.get_name()))
        else:
            print('DRAG MOTION destination={}, '.format(
                motion_source.get_child().get_children()[1].get_text()))

        return True

    def on_drag_data_get(self, widget, drag_context, data, info, time):

        # print('DRAG GET widget={}, context={}, data={}, info={}'.format(
        #     widget, drag_context, data, info))

        text = ','.join(self.get_names_of_selected_or_drag_source())

        data.set_text(text, -1)

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):

        print('DRAG RECEIVE in={}, x={}, y={}'.format(widget.get_name(), x, y))
        print('DRAG RECEIVE data={}, info={}'.format(data.get_text(), info))

        # Get Child under X,Y
        # insert at that location.

        destination = widget.get_child_at_pos(x, y)

        if destination:
            index = self.get_index_of(destination)
        else:
            index = None

        children_names_to_add = data.get_text().split(',')

        if self.is_drag_source:
            # We delay add() after remove() -- see drag_end.
            # We use the canonical name instead of the index
            # to avoid re-ordering problems when dragging in
            # same container from beginning to after.
            self.drag_widgets_to_add = (children_names_to_add, destination)

        else:
            for child_name in children_names_to_add:
                widget.add_item(child_name, index)

        # update preferences depending on self.name ?

    def on_drag_end(self, widget, *args, **kwargs):

        print('DRAG END in={}, same={}'.format(
            widget.get_name(), self.is_drag_source))

        # print('DRAG END args={}, kwargs={}'.format(
        #     args, kwargs))

        self.remove_items(self.get_names_of_selected_or_drag_source())

        if self.is_drag_source and self.drag_widgets_to_add:
            (children_names_to_add, destination) = self.drag_widgets_to_add

            for child_name in children_names_to_add:
                widget.add_item(child_name, self.get_index_of(destination))

        # Reset drag data on widget (self), and others.
        for sibling in widget.get_parent().get_children():
            try:
                sibling.reset_drag_data()

            except AttributeError:
                pass

        self.dialog.update_dnd_preferences()

        # update preferences depending on self.name ?

    # def on_drag_data_delete(self, *args, **kwargs):
    #     print('DRAG DELETE args={}, kwargs={}, '.format(
    #         args, kwargs))

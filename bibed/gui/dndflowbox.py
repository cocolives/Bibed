import os
import logging

from bibed.foundations import lprint, lprint_caller_name
from bibed.constants import BIBED_ICONS_DIR

from bibed.preferences import defaults

from bibed.gui.helpers import (
    flat_unclickable_button_in_hbox,
    vbox_with_icon_and_label,
    widget_properties,
    frame_defaults,
)
from bibed.gui.gtk import Gtk, Gdk


LOGGER = logging.getLogger(__name__)


DROP_TEXT_NAME = 'drop-object-here'  # '[ → ⋅ ← ]'


def get_child_name(child):

    try:
        # return child.get_child().get_children()[1].get_text()
        return child.get_child().get_name()

    except AttributeError:
        # print('\tWARNING:', child, 'has no child() or children().')
        return None


def dnd_scrolled_flowbox(name=None, title=None, dialog=None, child_type=None, child_widget=None, connect_to=None):

    if title is None:
        title = name.title()

    if child_widget is None:
        child_widget = 'simple'

    frame = frame_defaults(title)

    scrolled = widget_properties(
        Gtk.ScrolledWindow(),
        expand=True,
    )

    scrolled.set_policy(Gtk.PolicyType.NEVER,
                        Gtk.PolicyType.AUTOMATIC)

    # debug_widget(scrolled)

    flowbox = widget_properties(
        DnDFlowBox(name=name, dialog=dialog,
                   child_type=child_type,
                   child_widget=child_widget),
        expand=False,
    )

    flowbox.set_min_children_per_line(2)
    flowbox.set_max_children_per_line(3)

    flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
    flowbox.set_activate_on_single_click(False)
    flowbox.set_homogeneous(False)
    flowbox.set_can_focus(False)

    if connect_to:
        flowbox.connect('child-activated', connect_to)

    scrolled.add(flowbox)
    frame.add(scrolled)

    # scrolled.set_size_request(100, 100)
    flowbox.set_size_request(100, 100)

    return frame, scrolled, flowbox


class DnDFlowBox(Gtk.FlowBox):

    def __init__(self, *args, **kwargs):

        self.dialog     = kwargs.pop('dialog')
        self.child_type = kwargs.pop('child_type')
        child_widget    = kwargs.pop('child_widget')

        super().__init__(*args, **kwargs)

        assert self.child_type in ('type', 'field', )
        assert child_widget in ('simple', 'icon', )

        if child_widget == 'simple':
            self.build_child_func = self.build_child_flat
        else:
            self.build_child_func = self.build_child_with_icon

        self.setup_drag_and_drop()

    @property
    def children_labels(self):

        labels = defaults.types.labels.copy()

        labels.update(defaults.fields.labels.copy())

        # TODO: translate this.
        labels[DROP_TEXT_NAME] = 'Drop here!'

        # DROP_ICON_NAME =
        # 'insert-object-symbolic'
        # 'document-save-symbolic'
        # 'edit-select-symbolic'
        # 'find-location-symbolic'

        return labels

    def get_label(self, name):

        return self.children_labels[name].replace('_', '')

    def get_icon(self, name, size=None):

        if size is None:
            size = '48x48'

        base_path = os.path.join(BIBED_ICONS_DIR, self.child_type, size)

        icon_path = os.path.join(base_path, name + '.png')

        if not os.path.exists(icon_path):
            icon_path = os.path.join(base_path, 'default.png')

        return icon_path

    def build_child_flat(self, child_name):

        # if icon is None:
        #     # Could also be 'orientation-portrait-symbolic'
        #     icon_name = 'document-edit-symbolic'

        return flat_unclickable_button_in_hbox(
            child_name, self.get_label(child_name),
            icon_path=self.get_icon(child_name, '24x24'))

    def build_child_with_icon(self, child_name):

        return vbox_with_icon_and_label(
            child_name, self.get_label(child_name),
            icon_path=self.get_icon(child_name, '48x48'))

    # ——————————————————————————————————————————————————————— FlowBox overrides

    def add_item(self, child_name, index=None):

        # This should change dynamically, given where the
        # child is when the drag begin.
        # dnd_area.drag_source_set_icon_name(Gtk.STOCK_GO_FORWARD)

        child = self.build_child_func(child_name)

        if child_name == DROP_TEXT_NAME:
            child = widget_properties(child,
                                      classes=['dnd-drop-target'],
                                      can_focus=False)

        if index is None:
            # HEADS UP: index can be 0 (thus False)
            self.add(child)
        else:
            self.insert(child, index)

        # print('\tADD {} to {}'.format(child_name, index))

        # Necessary for add() after DnD operations,
        # because everything else is already shown.
        child.show_all()

    def add_items(self, children_names):

        for child_name in children_names:
            self.add_item(child_name)

    def remove_item(self, child_name, destroy=True):

        for child in self.get_children():
            if get_child_name(child) == child_name:
                self.remove(child)
                # print('\t\tREMOVE', child_name, 'IN', self.get_name())

                if destroy:
                    # destroy() will remove child from the container, but
                    # this it not always what we want, notably in conditions
                    # of drag-n-drop.
                    # Cf. https://lazka.github.io/pgi-docs/Gtk-3.0/classes/Container.html#Gtk.Container.remove  # NOQA
                    child.destroy()

        # print('CHILDREN after remove:', [
        #     (get_child_name(x),
        #      self.get_index_of(get_child_name(x)),
        #      )
        #     for x in self.get_children()
        # ])
        pass

    def remove_items(self, child_names=None):

        for child in self.get_children():
            if child_names is None:
                child.destroy()

            else:
                child_name = get_child_name(child)

                if child_name in child_names:
                    # destroy() will remove it from the container.
                    # Cf. https://lazka.github.io/pgi-docs/Gtk-3.0/classes/Container.html#Gtk.Container.remove  # NOQA
                    # print('\t\tREMOVE {}'.format(child_name))
                    child.destroy()

    def get_children_names(self):

        return [
            get_child_name(child)
            for child in self.get_children()
        ]

    def get_index_of(self, child_name, debug=False):

        # We could be trying to find index of a Gtk.Widget
        # or a child name (as string).
        is_str = isinstance(child_name, str)

        for index, _ in enumerate(self.get_children()):

            child_at_index = self.get_child_at_index(index)

            if is_str:
                if child_name == get_child_name(child_at_index):
                    # if debug:
                    #     print('INDEX by name', index)
                    return index
            else:
                if child_name == child_at_index:
                    # if debug:
                    #     print('INDEX by child', index)
                    return index

        return None

    def get_names_of_selected_or_drag_source(self):

        # Other things than the source selected ?
        selected = self.get_selected_children()

        names = set()

        if selected:
            names |= set([
                get_child_name(child)
                for child in selected
            ])

        if self.drag_motion_origin:
            # Add the drag origin in case it
            # was not selected before dragging.
            # Sometimes it's None if the user dragged
            # too fast for the motion to detect it.
            names |= set([get_child_name(self.drag_motion_origin)])

        return list(names)

    def get_siblings(self):

        my_viewport = self.get_parent()
        # print('MY VIEWPORT', my_viewport)

        my_scroll = my_viewport.get_parent()
        # print('MY SCROLL', my_scroll)

        my_frame = my_scroll.get_parent()
        # print('MY FRAME', my_frame)

        frame_container = my_frame.get_parent()
        # print('MY FRAME CONTAINER', frame_container)

        all_frames = frame_container.get_children()
        # print('ALL FRAMES', all_frames)

        all_flowboxes = [
            frame.get_child().get_child().get_child()
            for frame in all_frames

            # In preferences, we have labels
            # at the same level as the frames.
            if isinstance(frame, Gtk.Frame)
        ]

        return all_flowboxes

    # ————————————————————————————————————————————————————————————— DND methods

    def setup_drag_and_drop(self):

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

    def on_drag_begin(self, *args, **kwargs):

        # print('DRAG BEGIN in={}'.format(args[0].get_name()))

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

                self.replace_drag_origin()

                # try:
                #     print('DRAG MOTION origin={}'.format(
                #         get_child_name(motion_source)))
                # except AttributeError:
                #     pass

        else:
            self.remove_drop_target(only_others=True)

        if motion_source == self.drag_motion_destination:
            # We already noted that.
            return True

        # Overwrite at each motion to get destination (moving target).
        self.drag_motion_destination = motion_source

        # if motion_source is None:
        #     print('DRAG MOTION destination=<empty area> of {}'.format(
        #         widget.get_name()))
        # else:
        #     print('DRAG MOTION destination={}, '.format(
        #         get_child_name(motion_source)))

        self.update_drop_destination()

        return True

    def update_drop_destination(self):

        #
        # HEADS UP: order of doing things MATTERS A LOT!!
        #           Else indexes get lost or are messed up.

        try:
            destination_name = get_child_name(self.drag_motion_destination)

        except AttributeError:
            # Destination is empty space.
            destination_name = None

        if destination_name != DROP_TEXT_NAME:

            # target_index = self.get_index_of(DROP_TEXT_NAME)
            destination_index = self.get_index_of(destination_name)

            self.remove_drop_target()

            # print('TARGET', target_index,
            #       'MOVE TO', destination_name,
            #       destination_index)

            self.add_item(DROP_TEXT_NAME, destination_index)

    def on_drag_data_get(self, widget, drag_context, data, info, time):

        # print('DRAG GET widget={}, context={}, data={}, info={}'.format(
        #     widget, drag_context, data, info))

        text = ','.join(self.get_names_of_selected_or_drag_source())

        data.set_text(text, -1)

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):

        # print('DRAG RECEIVE in={}, x={}, y={}'.format(widget.get_name(), x, y))
        # print('DRAG RECEIVE data={}, info={}'.format(data.get_text(), info))

        # Get Child under X,Y
        # insert at that location.

        destination = widget.get_child_at_pos(x, y)

        # print('RECEIVE DESTINATION', get_child_name(destination))

        if destination:
            start_index = self.get_index_of(destination)
        else:
            start_index = None

        try:
            children_names_to_add = data.get_text().split(',')

        except AttributeError:
            self.abort_drag_and_drop()
            return

        if self.is_drag_source:
            # We delay add() after remove() -- see drag_end.
            # We use the canonical name instead of the index
            # to avoid re-ordering problems when dragging in
            # same container from beginning to after.
            self.drag_widgets_to_add = (children_names_to_add, start_index)

        else:
            # print('ADDING TO SIBLING')

            for index, child_name in enumerate(children_names_to_add):
                widget.add_item(child_name,
                                (start_index + index)
                                if start_index is not None
                                else -1)

            self.remove_drop_target()

        # update preferences depending on self.name ?

    def on_drag_end(self, widget, *args, **kwargs):

        # print('DRAG END in={}, same={}'.format(
        #     widget.get_name(), self.is_drag_source))

        # print('DRAG END args={}, kwargs={}'.format(
        #     args, kwargs))

        self.remove_items(self.get_names_of_selected_or_drag_source())

        # TODO: self.remove_items([self.drag_motion_origin])

        if self.is_drag_source and self.drag_widgets_to_add:
            # print('ADDING TO SELF')

            (children_names_to_add, start_index) = self.drag_widgets_to_add

            for index, child_name in enumerate(children_names_to_add):
                widget.add_item(child_name,
                                (start_index + index)
                                if start_index is not None
                                else -1)

        self.reset_drag_source_and_destinations()

        self.dialog.update_dnd_preferences()

        # update preferences depending on self.name ?

    # def on_drag_data_delete(self, *args, **kwargs):
    #     print('DRAG DELETE args={}, kwargs={}, '.format(
    #         args, kwargs))

    # ———————————————————————————————————————————————————————— DND auxilliaries

    def replace_drag_origin(self):

        origin_name = get_child_name(self.drag_motion_origin)
        origin_index = self.get_index_of(self.drag_motion_origin)

        # print('DRAG REMOVE ORIGIN: INSERT -drop- AT POSITION',
        #       origin_index,
        #       'THEN REMOVE',
        #       origin_name)

        self.add_item(DROP_TEXT_NAME, origin_index)
        self.remove_item(origin_name, destroy=False)

    def remove_drop_target(self, only_self=False, only_others=False):
        ''' remove the drop target from all drag source in case mouse changed destination container. '''

        if only_self:
            self.remove_item(DROP_TEXT_NAME)
            return

        # This will get self in the loop.
        siblings = self.get_siblings()

        if only_others:
            # print('REMOVE IN OTHERS', self, siblings)
            siblings.remove(self)

        for sibling in siblings:
            try:
                sibling.remove_item(DROP_TEXT_NAME)

            except AttributeError:
                pass

    def reset_drag_source_and_destinations(self):
        ''' Reset drag data on widget (self), and others of same level. '''

        # This will get self in the loop.
        siblings = self.get_siblings()

        for sibling in siblings:
            try:
                sibling.reset_drag_data()

            except AttributeError:
                pass

    def reset_drag_data(self):

        self.is_drag_source = False
        self.drag_motion_origin = None
        self.drag_motion_destination = None
        self.drag_widgets_to_add = None

        self.remove_drop_target(only_self=True)

    def abort_drag_and_drop(self):

        self.add_item(get_child_name(self.drag_motion_origin))

        self.reset_drag_source_and_destinations()


import logging

from bibed.gui.gtk import Gtk, Gdk
from bibed.gui.helpers import (
    flat_unclickable_button,
)


LOGGER = logging.getLogger(__name__)


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

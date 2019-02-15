
from bibed.gtk import Gtk


class BibedStack(Gtk.Stack):

    def __init__(self, window):
        super().__init__()

        self.window = window

        self.connect('notify::visible-child', self.visible_child_changed)

    def is_child_visible(self, name):

        return self.get_visible_child_name() == name

    def visible_child_changed(self, stack, child, *args):

        self.window.sync_buttons_states()

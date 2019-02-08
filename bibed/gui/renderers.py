
from bibed.constants import CELLRENDERER_PIXBUF_PADDING
from bibed.gtk import GObject, Gtk


class CellRendererTogglePixbuf(Gtk.CellRendererPixbuf):

    __gsignals__ = {
        'clicked': (
            GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_STRING, )
        )
    }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.set_property('mode', Gtk.CellRendererMode.ACTIVATABLE)
        self.set_padding(CELLRENDERER_PIXBUF_PADDING,
                         CELLRENDERER_PIXBUF_PADDING)

    def do_activate(self, event, widget, path, background_area, cell_area, flags):

        self.emit('clicked', path)

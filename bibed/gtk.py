import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Notify', '0.7')

from gi.repository import (  # NOQA
    GObject,
    GLib,
    Gio,
    Gtk,
    Gdk,
    GdkPixbuf,
    Pango,
    Notify
)

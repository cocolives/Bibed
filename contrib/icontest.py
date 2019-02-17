
import os

from bibed.constants import (
    APP_NAME,
    GRID_BORDER_WIDTH,
    GRID_COLS_SPACING,
    GRID_ROWS_SPACING,
)

from bibed.gtk import Gtk, Gio
from bibed.preferences import defaults
from bibed.gui.helpers import (
    label_with_markup,
    widget_properties,
    in_scrolled,
    bibed_icon_name,
)
from bibed.gui.css import GtkCssAwareMixin

bibed_lower = APP_NAME.lower()
home_path = os.path.expanduser('~')
needed_sizes = [16, 24, 32, 48, 64, 96, 128, 256, 512]


def format_icon_path(string):

    string = string.replace(home_path, '~')

    if bibed_lower in string:
        return '<b>{}</b>'.format(string)

    return string


class BibedIconTestWindow(Gtk.Window, GtkCssAwareMixin):

    def __init__(self):
        super().__init__()

        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_default_size(600, 500)

        self.setup_resources_and_css()

        self.grid = Gtk.Grid()
        self.grid.set_border_width(GRID_BORDER_WIDTH)
        self.grid.set_row_spacing(GRID_ROWS_SPACING / 2)
        self.grid.set_column_spacing(GRID_COLS_SPACING / 2)

        columns_count = 4
        column_index = 0
        row_index = 1

        self.grid.attach(label_with_markup(
            'Icon search path: <small><span font="monospace" '
            'color="grey">{}</span></small>'.format(
                ', '.join(format_icon_path(x)
                          for x in self.icon_theme.get_search_path())),
            justify=Gtk.Justification.CENTER,
            line_wrap=True,
            # ellipsize=Pango.EllipsizeMode.MIDDLE,
        ), 0, 0, columns_count, 1)

        for typee_name, typee_label in defaults.types.labels.items():

            vbox = widget_properties(
                Gtk.VBox(),
                expand=True,
                halign=Gtk.Align.FILL,
                valign=Gtk.Align.FILL,
            )

            icon_name = bibed_icon_name('type', typee_name)

            gicon = Gio.ThemedIcon(name=icon_name)

            sizes = set(self.icon_theme.get_icon_sizes(icon_name))

            icon = Gtk.Image.new_from_gicon(gicon, icon_size)


            missing = sorted([
                size for size in needed_sizes if size not in sizes
            ])

            if missing and sizes:
                print(icon_name, sizes)

            if sizes:
                # icon = Gtk.Image.new_from_gicon(gicon, Gtk.IconSize.DIALOG)
                picon = self.icon_theme.load_icon(
                    icon_name, 64,
                    0)

            else:
                picon = self.icon_theme.load_icon(
                    self.icon_theme.get_example_icon_name(),
                    64,
                    Gtk.IconLookupFlags.GENERIC_FALLBACK)

            vbox.pack_start(Gtk.Image.new_from_pixbuf(picon), True, True, 0)

            label = label_with_markup(
                '{}\n<small><span color="grey"><span font="monospace">@{}</span>, <span font="monospace">{}</span>\n{}</span></small>'.format(
                    typee_label, typee_name, icon_name,
                    ('missing: {}'.format(', '.join(str(s) for s in missing))
                     if missing else '<i><span color="green">All sizes OK</span></i>') if sizes else '<b><span color="red">No icon yet</span></b>',
                ),
                xalign=0.5,
                justify=Gtk.Justification.CENTER,
                # ellipsize=Pango.EllipsizeMode.MIDDLE,
            )

            vbox.pack_start(label, True, False, 0)

            self.grid.attach(vbox, column_index, row_index, 1, 1)

            column_index += 1

            if column_index % columns_count == 0:
                column_index = 0
                row_index += 1

        self.add(in_scrolled(self.grid))


if __name__ == '__main__':
    win = BibedIconTestWindow()
    win.connect('destroy', Gtk.main_quit)
    win.show_all()

    try:
        Gtk.main()

    except KeyboardInterrupt:
        pass

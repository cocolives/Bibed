
import logging

# from bibed.foundations import ldebug
from bibed.constants import (
    SEARCH_SPECIALS,
    GRID_COLS_SPACING,
)

# from bibed.exceptions import BibedTreeViewException
# from bibed.preferences import memories  # , gpod

# from bibed.gui.renderers import CellRendererTogglePixbuf
# from bibed.gui.treemixins import BibedEntryTreeViewMixin
from bibed.gui.gtk import Gtk


LOGGER = logging.getLogger(__name__)


class BibedSearchBar(Gtk.SearchBar):

    def __init__(self, search_entry):

        super().__init__()

        self.search = search_entry

        self.set_show_close_button(True)

        grid = Gtk.Grid()
        grid.set_column_homogeneous(True)
        grid.set_column_spacing(GRID_COLS_SPACING)

        help_label = Gtk.Label()

        help_label.set_markup(
            '<span size="small">'
            + '  '.join(
                '<span font="monospace"><b>{char}:</b></span><span '
                'color="grey">{label}</span>'.format(
                    char=char, label=label)
                for char, index, label in SEARCH_SPECIALS
            )
            + '</span>'
        )

        fill_label = Gtk.Label()

        grid.attach(help_label, 0, 0, 1, 1)
        grid.attach_next_to(
            self.search, help_label,
            Gtk.PositionType.RIGHT,
            1, 1)
        grid.attach_next_to(
            fill_label, self.search,
            Gtk.PositionType.RIGHT,
            1, 1)

        self.connect_entry(self.search)

        self.grid = grid

        self.add(self.grid)

        self.show_all()

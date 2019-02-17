
import logging

from bibed.ltrace import lprint_function_name, lprint_caller_name

from bibed.constants import (
    SEARCH_SPECIALS,
    GRID_COLS_SPACING,
    SEARCH_WIDTH_MINIMAL,
    SEARCH_WIDTH_MAXIMAL,
)

from bibed.decorators import run_at_most_every
from bibed.gtk import Gtk, Gdk, Pango
from bibed.gui.helpers import label_with_markup


LOGGER = logging.getLogger(__name__)


def help_markup(help_items):
    return '<span size="small">{}</span>'.format(
        '  '.join(
            '<span font="monospace"><b>{char}:</b></span><span '
            'color="grey">{label}</span>'.format(
                char=char, label=label)
            for char, index, label in help_items
        )
    )


class BibedSearchBar(Gtk.SearchBar):

    def __init__(self, search_entry):

        super().__init__()

        self.search = search_entry

        self.search.props.width_chars = SEARCH_WIDTH_EXPANDED

        self.set_show_close_button(True)

        grid = Gtk.Grid()
        # grid.set_column_homogeneous(True)
        grid.set_column_spacing(GRID_COLS_SPACING)

        half_help_count = int(len(SEARCH_SPECIALS) / 2)

        help_label_left = Gtk.Label()
        help_label_left.set_markup(
            help_markup(SEARCH_SPECIALS[:half_help_count])
        )

        help_label_right = Gtk.Label()
        help_label_right.set_markup(
            help_markup(SEARCH_SPECIALS[half_help_count:])
        )

        grid.attach(help_label_left, 0, 0, 1, 1)
        grid.attach_next_to(
            self.search, help_label_left,
            Gtk.PositionType.RIGHT,
            1, 1)
        grid.attach_next_to(
            help_label_right, self.search,
            Gtk.PositionType.RIGHT,
            1, 1)

        self.connect_entry(self.search)

        self.grid = grid

        self.add(self.grid)

        self.show_all()

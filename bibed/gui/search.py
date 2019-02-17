
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

    def __init__(self, search_entry, treeview):

        super().__init__()

        self.search = search_entry
        self.treeview = treeview

        self.set_show_close_button(True)

        grid = Gtk.Grid()
        # grid.set_column_homogeneous(True)
        grid.set_column_spacing(GRID_COLS_SPACING)

        half_help_count = int(len(SEARCH_SPECIALS) / 2)

        help_label_left = label_with_markup(
            help_markup(SEARCH_SPECIALS[:half_help_count]),
            ellipsize=Pango.EllipsizeMode.START,
        )

        help_label_right = label_with_markup(
            help_markup(SEARCH_SPECIALS[half_help_count:]),
            ellipsize=Pango.EllipsizeMode.END,
        )

        # left, top, width, height
        grid.attach(help_label_left, 0, 0, 1, 1)
        grid.attach(self.search, 1, 0, 1, 1)
        grid.attach(help_label_right, 2, 0, 1, 1)

        self.connect_entry(self.search)

        self.grid = grid

        self.add(self.grid)

        self.connect('size-allocate', self.on_size_allocate)

        self.show_all()

    def set_search_mode(self, mode):

        super().set_search_mode(mode)

        if mode:
            # Be sure we re-grab the focus, even if already open,
            # else a Control-F while browsing the treeview does
            # not refocus the search entry and we're stuck.
            self.search.grab_focus()

    @run_at_most_every(500)
    def on_size_allocate(self, widget, rectangle):

        try:
            previous_allocation = self.previous_allocation

        except AttributeError:
            pass

        else:
            if previous_allocation.width == rectangle.width:
                # Avoid superflous calls (numerous on Alt-Tab)
                return

        possible_width = int(rectangle.width / 2.5 / 12)

        if possible_width < SEARCH_WIDTH_MINIMAL:
            possible_width = SEARCH_WIDTH_MINIMAL

        if possible_width > SEARCH_WIDTH_MAXIMAL:
            possible_width = SEARCH_WIDTH_MAXIMAL

        self.search.props.width_chars = possible_width

        self.previous_allocation = rectangle

import logging

# from bibed.foundations import ldebug
from bibed.constants import (
    COL_PIXBUF_WIDTH,
    CELLRENDERER_PIXBUF_PADDING,
)
from bibed.exceptions import BibedTreeViewException
from bibed.preferences import preferences, memories, gpod

from bibed.gui.renderers import CellRendererTogglePixbuf
from bibed.gui.treemixins import BibedEntryTreeViewMixin
from bibed.gtk import Gtk, Pango


LOGGER = logging.getLogger(__name__)


class BibedMainTreeView(Gtk.TreeView, BibedEntryTreeViewMixin):
    ''' Wraps :class:`Gtk.TreeView` with BibedEntry specifics. '''

    def __init__(self, *args, **kwargs):
        ''' Create the treeview.

            :param:window: the main window.
            :param:a primary clipboard: the main window.
        '''

        self.main_model  = kwargs.get('model')
        self.application = kwargs.pop('application')
        self.clipboard   = kwargs.pop('clipboard')
        self.window      = kwargs.pop('window')
        self.files       = self.application.files

        super().__init__(*args, **kwargs)

        try:
            # Subclasses implementations, not required.
            self.setup_pixbufs()

        except AttributeError:
            pass

        # We get better search via global SearchEntry
        self.set_enable_search(False)

        try:
            self.setup_treeview_columns()

        except AttributeError:
            raise BibedTreeViewException('Subclasses must implement setup_treeview_columns()')

        self.set_fixed_height_mode(True)

        try:
            if gpod('treeview_show_tooltips'):
                # Not required neither.
                self.set_tooltip_column(self.TOOLTIP_COLUMN)

        except AttributeError:
            pass

        try:
            # Not required neither.
            self.connect('row-activated', self.on_treeview_row_activated)

        except AttributeError:
            pass

        self.selection = self.get_selection()
        self.selection.set_mode(self.SELECTION_MODE)

        try:
            # Not required neither.
            self.selection.connect('changed', self.on_selection_changed)

        except AttributeError:
            pass

    def setup_text_column(self, name, store_num, attributes=None, resizable=False, expand=False, min=None, max=None, xalign=None, ellipsize=None):  # NOQA

        if ellipsize is None:
            ellipsize = Pango.EllipsizeMode.NONE

        if attributes is None:
            attributes = {}

        column = Gtk.TreeViewColumn(name)

        if xalign is not None:
            cellrender = Gtk.CellRendererText(
                xalign=xalign, ellipsize=ellipsize)
        else:
            cellrender = Gtk.CellRendererText(ellipsize=ellipsize)

        column.pack_start(cellrender, True)

        column.add_attribute(cellrender, 'markup', store_num)

        for attr_name, column_num in attributes.items():
            column.add_attribute(cellrender, attr_name, column_num)

        column.set_sort_column_id(store_num)

        column.set_reorderable(True)
        column.set_resizable(False)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

        column.connect('clicked', self.on_treeview_column_clicked)

        self.append_column(column)

        return column

    def setup_pixbuf_column(self, title, store_num, renderer_method, signal_method=None):

        if signal_method:
            renderer = CellRendererTogglePixbuf()

        else:
            renderer = Gtk.CellRendererPixbuf()
            renderer.set_padding(CELLRENDERER_PIXBUF_PADDING,
                                 CELLRENDERER_PIXBUF_PADDING)

        column = Gtk.TreeViewColumn(title)
        column.pack_start(renderer, False)

        column.set_sort_column_id(store_num)

        column.set_reorderable(True)
        column.set_resizable(False)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_fixed_width(COL_PIXBUF_WIDTH)

        column.set_cell_data_func(renderer, renderer_method)

        if signal_method is not None:
            renderer.connect('clicked', signal_method)

        column.connect('clicked', self.on_treeview_column_clicked)

        self.append_column(column)

        return column

    def do_status_change(self, message):

        return self.window.do_status_change(message)

    def do_column_sort(self):

        if memories.treeview_sort_column is not None:

            for col in self.get_columns():
                if col.props.title == memories.treeview_sort_column:

                    # print('COL', col.props.title)
                    # print(col.get_sort_order())
                    col.props.sort_order = memories.treeview_sort_order
                    # print(col.get_sort_order())

                    # print(col.get_sort_indicator())
                    col.props.sort_indicator = memories.treeview_sort_indicator
                    # print(col.get_sort_indicator())
                    break

    def switch_tooltips(self, state=None):

        tooltip_column = getattr(self, 'TOOLTIP_COLUMN', None)

        if tooltip_column is None:
            return

        def switch_off():
            self.set_tooltip_column(-1)

            # Autosave is ON, because direct attribute.
            preferences.treeview_show_tooltips = False

        def switch_on():
            self.set_tooltip_column(self.TOOLTIP_COLUMN)

            # Autosave is ON, because direct attribute.
            preferences.treeview_show_tooltips = True

        if state is None:
            if self.get_tooltip_column() == -1:
                switch_on()
            else:
                switch_off()
        else:
            if state:
                switch_on()
            else:
                switch_off()

        self.do_status_change('Tooltips switched {}.'.format(
            'off' if self.get_tooltip_column() == -1 else 'ON'
        ))

    # ——————————————————————————————————————————————————————— Generic selection

    def unselect_all(self):
        ''' Simple wrapper for one-line call. '''

        self.selection.unselect_all()

    def get_selected(self):
        ''' Simple wrapper for one-line call. '''

        model, treeiter = self.selection.get_selected()

        return model, treeiter

    def get_selected_row(self):

        # Code to add to connect a method to new selection.
        # selection.connect('changed', self.on_treeview_selection_changed)
        # selection.unselect_all()

        model, treeiter = self.get_selected()

        if treeiter is None:
            return None
        else:
            return model[treeiter]

    def get_selected_rows(self, paths_only=False):

        model, paths = self.selection.get_selected_rows()

        if paths:
            if paths_only:
                return paths
            else:
                # Gtk.TreeRowReference.new(model, path)
                return [model[model.get_iter(path)] for path in paths]
        else:
            return None

    # ————————————————————————————————————————————————————————————————— Signals

    def on_treeview_column_clicked(self, column):

        coltit = column.props.title
        colidc = column.props.sort_indicator
        colord = column.props.sort_order

        if memories.treeview_sort_column is None:
            memories.treeview_sort_column = coltit
            memories.treeview_sort_indicator = colidc
            memories.treeview_sort_order = colord

        else:
            if memories.treeview_sort_column != coltit:
                memories.treeview_sort_column = coltit

            if memories.treeview_sort_indicator != colidc:
                memories.treeview_sort_indicator = colidc

            if memories.treeview_sort_order != colord:
                memories.treeview_sort_order = colord

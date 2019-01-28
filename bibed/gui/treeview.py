import logging

from bibed.constants import (
    # BIBED_ICONS_DIR,
    FILES_COMBO_DEFAULT_WIDTH,
    RESIZE_SIZE_MULTIPLIER,
    BibAttrs,
)

from bibed.preferences import memories  # , gpod
from bibed.entry import BibedEntry

from bibed.gui.entry import BibedEntryDialog
from bibed.gui.gtk import Gtk, Pango


LOGGER = logging.getLogger(__name__)


class BibedMainTreeView(Gtk.TreeView):
    ''' Wraps :class:`Gtk.TreeView`

    '''

    def __init__(self, *args, **kwargs):
        ''' Return the treeview.

            :param:window: the main window.
            :param:a primary clipboard: the main window.
        '''

        self.main_model  = kwargs.get('model')
        self.application = kwargs.pop('application')
        self.clipboard   = kwargs.pop('clipboard')
        self.window      = kwargs.pop('window')

        super().__init__(*args, **kwargs)

        # We get better search via global SearchEntry
        self.set_enable_search(False)

        self.col_global_id = self.add_treeview_text_column(
            '#', BibAttrs.GLOBAL_ID)
        self.col_id = self.add_treeview_text_column('#', BibAttrs.ID)
        self.col_id.props.visible = False

        self.col_type = self.add_treeview_text_column('type', BibAttrs.TYPE)

        # missing columns (icons)

        self.col_key = self.add_treeview_text_column(
            'key', BibAttrs.KEY, resizable=True,
            min=100, max=150, ellipsize=Pango.EllipsizeMode.START)
        self.col_author = self.add_treeview_text_column(
            'author', BibAttrs.AUTHOR, resizable=True,
            min=130, max=200, ellipsize=Pango.EllipsizeMode.END)
        self.col_title = self.add_treeview_text_column(
            'title', BibAttrs.TITLE, resizable=True, expand=True,
            min=300, ellipsize=Pango.EllipsizeMode.MIDDLE)
        self.col_journal = self.add_treeview_text_column(
            'journal', BibAttrs.JOURNAL, resizable=True,
            min=130, max=200, ellipsize=Pango.EllipsizeMode.END)

        self.col_year = self.add_treeview_text_column(
            'year', BibAttrs.YEAR, xalign=1)

        # missing columns (icons)

        select = self.get_selection()
        select.connect("changed", self.on_treeview_selection_changed)

        self.connect('row-activated', self.on_treeview_row_activated)

        select.unselect_all()

    def do_status_change(self, message):

        return self.window.do_status_change(message)

    def add_treeview_text_column(self, name, store_num, resizable=False, expand=False, min=None, max=None, xalign=None, ellipsize=None):  # NOQA

        if ellipsize is None:
            ellipsize = Pango.EllipsizeMode.NONE

        column = Gtk.TreeViewColumn(name)

        column.connect('clicked', self.on_treeview_column_clicked)

        if xalign is not None:
            cellrender = Gtk.CellRendererText(
                xalign=xalign, ellipsize=ellipsize)
        else:
            cellrender = Gtk.CellRendererText(ellipsize=ellipsize)

        column.pack_start(cellrender, True)
        column.add_attribute(cellrender, "text", store_num)
        column.set_sort_column_id(store_num)

        if resizable:
            column.set_resizable(True)

        if expand:
            column.set_expand(True)

        if min is not None:
            # column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_min_width(min)
            column.set_fixed_width(min)

        if max is not None:
            # column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_max_width(min)

            # column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.append_column(column)

        return column

    def columns_autosize(self, current_width):
        # Remove 1 else the treeview gets a few pixels too wide.
        # The last column will compensate any "missing" pixels,
        # and we get no horizontal scrollbar.
        column_width = round(current_width * RESIZE_SIZE_MULTIPLIER) - 1

        self.col_key.set_min_width(column_width)
        self.col_author.set_min_width(column_width)
        self.col_journal.set_min_width(column_width)

        self.columns_autosize()

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

    def on_treeview_row_activated(self, treeview, path, column):

        # Are we on the list store, or a filter ?
        model = self.get_model()
        files = self.application.files

        treeiter = model.get_iter(path)

        # value = store.get_value(treeiter, 1)
        bib_key = model[treeiter][BibAttrs.KEY]
        global_id = model[treeiter][BibAttrs.GLOBAL_ID]
        filename = model[treeiter][BibAttrs.FILENAME]

        entry = files[filename].get_entry_by_key(bib_key)

        # This is needed to update the treeview after modifications.
        entry.gid = global_id

        assert(isinstance(entry, BibedEntry))

        entry_edit_dialog = BibedEntryDialog(
            parent=self.window, entry=entry)

        entry_edit_dialog.run()

        # TODO: convert this test to Gtk.Response.OK and CANCEL
        #       to know if we need to insert/update or not.
        if entry.database is not None and entry_edit_dialog.can_save:
            # TODO: update list_store directly.
            # Entry was saved to disk, insert it in the treeview.
            self.main_model.update_entry(entry)

        entry_edit_dialog.destroy()

    def on_treeview_selection_changed(self, selection):

        model, treeiter = selection.get_selected()

        if treeiter is None:
            self.do_status_change("Nothing selected.")

        else:
            bib_key = model[treeiter][BibAttrs.KEY]

            if bib_key:
                to_copy = BibedEntry.single_bibkey_format(bib_key)

                self.clipboard.set_text(to_copy, len=-1)

                self.do_status_change(
                    "“{1}” copied to clipboard (from row {0}).".format(
                        model[treeiter][BibAttrs.ID], to_copy))
            else:
                self.do_status_change(
                    "Selected row {0}.".format(model[treeiter][BibAttrs.ID]))

    def do_column_sort(self):

        if memories.treeview_sort_column is not None:
            # print('setting column')

            for col in self.get_columns():
                if col.props.title == memories.treeview_sort_column:

                    # print('COL', col.props.title)
                    # print(col.get_sort_order())
                    col.props.sort_order = memories.treeview_sort_order
                    # print(col.get_sort_order())
                    # print(col.get_sort_indicator())
                    col.props.sort_indicator = memories.treeview_sort_indicator
                    # print(col.get_sort_indicator())

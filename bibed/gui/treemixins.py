
import webbrowser

# from bibed.foundations import ldebug
from bibed.constants import (
    BibAttrs,
    FileTypes,
    URL_PIXBUFS,
    FILE_PIXBUFS,
    COMMENT_PIXBUFS,
    READ_STATUS_PIXBUFS,
    QUALITY_STATUS_PIXBUFS,
    COL_KEY_WIDTH,
    COL_TYPE_WIDTH,
    COL_YEAR_WIDTH,
    COL_PIXBUF_WIDTH,
    COL_AUTHOR_WIDTH,
    COL_JOURNAL_WIDTH,
    COL_SEPARATOR_WIDTH,
)

from bibed.preferences import memories  # , gpod
from bibed.entry import BibedEntry

from bibed.gui.entry import BibedEntryDialog
from bibed.gui.gtk import Gtk, Pango, GdkPixbuf


class BibedEntryTreeViewMixin:
    ''' This class exists only to separate entry-related actions
        from pure-treeview ones. '''

    TOOLTIP_COLUMN = BibAttrs.TOOLTIP
    SELECTION_MODE = Gtk.SelectionMode.MULTIPLE

    def setup_pixbufs(self):

        for attr_name, constant_dict in (
            ('quality_status_pixbufs', QUALITY_STATUS_PIXBUFS),
            ('read_status_pixbufs', READ_STATUS_PIXBUFS),
            ('comment_pixbufs', COMMENT_PIXBUFS),
            ('file_pixbufs', FILE_PIXBUFS),
            ('url_pixbufs', URL_PIXBUFS),
        ):
            temp_dict = {}

            for status, icon in constant_dict.items():
                if icon:
                    temp_dict[status] = GdkPixbuf.Pixbuf.new_from_file(icon)
                else:
                    temp_dict[status] = None

            setattr(self, attr_name, temp_dict)

    def setup_treeview_columns(self):

        self.col_key = self.setup_text_column(
            'key', BibAttrs.KEY,
            ellipsize=Pango.EllipsizeMode.START,
            attributes={'foreground': BibAttrs.COLOR},
        )

        self.col_type = self.setup_text_column(
            'type', BibAttrs.TYPE,
            attributes={'foreground': BibAttrs.COLOR},
        )

        # DOI column

        # TODO: integrate a pixbuf for 'tags' (keywords) ?

        self.col_file = self.setup_pixbuf_column(
            'F', BibAttrs.FILE,
            self.get_file_cell_column,
            self.on_file_clicked)
        self.col_url = self.setup_pixbuf_column(
            'U', BibAttrs.URL,
            self.get_url_cell_column,
            self.on_url_clicked)
        self.col_quality = self.setup_pixbuf_column(
            'Q', BibAttrs.QUALITY,
            self.get_quality_cell_column,
            self.on_quality_clicked)
        self.col_read = self.setup_pixbuf_column(
            'R', BibAttrs.READ,
            self.get_read_cell_column,
            self.on_read_clicked)
        self.col_comment = self.setup_pixbuf_column(
            'C', BibAttrs.COMMENT,
            self.get_comment_cell_column)

        self.col_author = self.setup_text_column(
            'author', BibAttrs.AUTHOR,
            ellipsize=Pango.EllipsizeMode.END,
            attributes={'foreground': BibAttrs.COLOR},
        )
        self.col_title = self.setup_text_column(
            'title', BibAttrs.TITLE,
            ellipsize=Pango.EllipsizeMode.MIDDLE,
            attributes={'foreground': BibAttrs.COLOR},
        )
        self.col_journal = self.setup_text_column(
            'journal', BibAttrs.JOURNAL,
            ellipsize=Pango.EllipsizeMode.END,
            attributes={'foreground': BibAttrs.COLOR},
        )

        self.col_year = self.setup_text_column(
            'year', BibAttrs.YEAR, xalign=1.0,
            attributes={'foreground': BibAttrs.COLOR},
        )

        self.set_columns_widths(self.window.current_size[0])

    def set_columns_widths(self, width):

        col_key_width     = round(width * COL_KEY_WIDTH)
        col_type_width    = round(width * COL_TYPE_WIDTH)
        col_author_width  = round(width * COL_AUTHOR_WIDTH)
        col_journal_width = round(width * COL_JOURNAL_WIDTH)
        col_year_width    = round(width * COL_YEAR_WIDTH)
        col_title_width   = round(width - (
            col_key_width + col_author_width
            + col_journal_width + col_year_width
            + col_type_width
            + 5 * COL_PIXBUF_WIDTH
        ) - COL_SEPARATOR_WIDTH * 10)

        # print(col_key_width, col_type_width, col_author_width, col_journal_width, col_year_width, col_title_width, )

        self.col_key.set_fixed_width(col_key_width)
        self.col_type.set_fixed_width(col_type_width)
        self.col_author.set_fixed_width(col_author_width)
        self.col_journal.set_fixed_width(col_journal_width)
        self.col_title.set_fixed_width(col_title_width)
        self.col_year.set_fixed_width(col_year_width)

    # ————————————————————————————————————————————————————————— Pixbufs columns

    def get_read_cell_column(self, col, cell, model, iter, user_data):
            cell.set_property(
                'pixbuf', self.read_status_pixbufs[
                    model.get_value(iter, BibAttrs.READ)])

    def get_quality_cell_column(self, col, cell, model, iter, user_data):
            cell.set_property(
                'pixbuf', self.quality_status_pixbufs[
                    model.get_value(iter, BibAttrs.QUALITY)])

    def get_comment_cell_column(self, col, cell, model, iter, user_data):
            cell.set_property(
                'pixbuf', self.comment_pixbufs[
                    model.get_value(iter, BibAttrs.COMMENT) != ''])

    def get_url_cell_column(self, col, cell, model, iter, user_data):
            cell.set_property(
                'pixbuf', self.url_pixbufs[
                    model.get_value(iter, BibAttrs.URL) != ''])

    def get_file_cell_column(self, col, cell, model, iter, user_data):
            cell.set_property(
                'pixbuf', self.file_pixbufs[
                    model.get_value(iter, BibAttrs.FILE) != ''])

    # ———————————————————————————————————————————————————————— Entry selection

    def get_main_iter_by_gid(self, gid):

        # for row in self.main_model:
        #     if row[BibAttrs.GLOBAL_ID] == gid:
        #         return row.iter

        # TODO: make clear while I need to substract 1.
        #       make all counters equal everywhere.
        return self.main_model.get_iter(gid - 1)

    def get_entry_by_path(self, path, with_global_id=False, return_iter=False, only_row=False):

        # Are we on the list store, or a filter ?
        model     = self.get_model()
        treeiter  = model.get_iter(path)

        if only_row:
            return model[treeiter]

        bib_key   = model[treeiter][BibAttrs.KEY]
        filename  = model[treeiter][BibAttrs.FILENAME]

        entry = self.files.get_entry_by_key(bib_key, filename=filename)

        if with_global_id:
            entry.gid = model[treeiter][BibAttrs.GLOBAL_ID]

        if return_iter:
            return (entry, treeiter, )

        return entry

    def get_selected_entry(self):
        ''' Used in Gtk.SelectionMode.SINGLE. '''

        model, treeiter = self.get_selected()

        return self.get_entry_by_path(model.get_path(treeiter),
                                      with_global_id=True)

    def get_selected_entries(self):
        ''' Used in Gtk.SelectionMode.MULTIPLE. '''

        paths = self.get_selected_rows(paths_only=True)

        return [
            self.get_entry_by_path(path, with_global_id=True)
            for path in paths
        ]
    # ————————————————————————————————————————————————————————————— Gtk signals

    def on_quality_clicked(self, renderer, path):

        entry = self.get_entry_by_path(path, with_global_id=True)

        entry.toggle_quality()

        self.main_model[
            # TODO: Shouldn't we use get_real_path_from_path()
            #       or something like that? a Gtk method.
            self.get_main_iter_by_gid(entry.gid)
        ][BibAttrs.QUALITY] = entry.quality

        # if gpod('bib_auto_save'):
        self.files.trigger_save(entry.database.filename)

    def on_read_clicked(self, renderer, path):

        entry = self.get_entry_by_path(path, with_global_id=True)

        entry.cycle_read_status()

        self.main_model[
            self.get_main_iter_by_gid(entry.gid)
        ][BibAttrs.READ] = entry.read_status

        # if gpod('bib_auto_save'):
        self.files.trigger_save(entry.database.filename)

    def on_url_clicked(self, renderer, path):

        self.open_url_in_webbrowser(
            entry=self.get_entry_by_path(path, only_row=True))

    def on_file_clicked(self, renderer, path):

        self.open_file_in_prefered_application(
            self.get_entry_by_path(path, only_row=True))

    def on_treeview_row_activated(self, treeview, path, column):

        # GLOBAL_ID is needed to update the treeview after modifications.
        entry = self.get_entry_by_path(path, with_global_id=True)

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

    # ——————————————————————————————————————————————————————————— Entry actions

    def copy_to_clipboard_or_action(self, field_index, transform_func=None, action_func=None, action_message=None, row=None):

        if row is None:
            row = self.get_selected_row()
        else:
            row = row

        if row is None:
            self.do_status_change(
                'Nothing selected; nothing copied to clipboard.')
            return

        entry_gid  = row[BibAttrs.GLOBAL_ID]
        entry_data = row[field_index]

        if entry_data:
            transformed_data = (
                entry_data if transform_func is None
                else transform_func(entry_data)
            )

            if action_func is None:
                self.clipboard.set_text(transformed_data, len=-1)

                self.do_status_change(
                    '“{data}” copied to clipboard (from entry {key}).'.format(
                        data=transformed_data, key=entry_gid))

            else:
                action_func(transformed_data)

                self.do_status_change(
                    '“{data}” {message} (from entry {key}).'.format(
                        data=transformed_data,
                        message=('run through {func}'.format(
                            func=action_func.__name__)
                            if action_message is None
                            else action_message
                        ),
                        key=entry_gid,
                    )
                )

        else:
            self.do_status_change('Selected entry {key}.'.format(key=entry_gid))

    def copy_raw_key_to_clipboard(self, row=None):
        return self.copy_to_clipboard_or_action(BibAttrs.KEY, row=row)

    def copy_url_to_clipboard(self, row=None):
        return self.copy_to_clipboard_or_action(BibAttrs.URL, row=row)

    def copy_single_key_to_clipboard(self, row=None):
        return self.copy_to_clipboard_or_action(
            BibAttrs.KEY,
            transform_func=BibedEntry.single_bibkey_format,
            row=row,
        )

    def open_url_in_webbrowser(self, row=None):
        return self.copy_to_clipboard_or_action(
            BibAttrs.URL,
            action_func=webbrowser.open_new_tab,
            action_message='opened in web browser',
            row=row,
        )

    def open_file_in_prefered_application(self, row=None):

        # TODO: and an action to open in file browser.

        # return self.copy_to_clipboard_or_action(
        #     BibAttrs.KEY,
        #     action_func=webbrowser.open_new_tab,
        #     action_message='opened in web browser',
        #     entry=entry,
        # )
        pass

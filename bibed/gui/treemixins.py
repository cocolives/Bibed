
from bibed.ltrace import lprint_function_name, lprint_caller_name

from bibed.constants import (
    BibAttrs,
    URL_PIXBUFS,
    FILE_PIXBUFS,
    COMMENT_PIXBUFS,
    READ_STATUS_PIXBUFS,
    QUALITY_STATUS_PIXBUFS,
    COL_KEY_WIDTH,
    COL_TYPE_WIDTH,
    COL_YEAR_WIDTH,
    # COL_PIXBUF_WIDTH,
    COL_AUTHOR_WIDTH,
    COL_JOURNAL_WIDTH,
    # COL_SEPARATOR_WIDTH,
)

from bibed.decorators import only_one_when_idle
from bibed.utils import (
    open_with_system_launcher,
    open_urls_in_web_browser,
)
# from bibed.preferences import memories  # , gpod
from bibed.entry import BibedEntry
from bibed.locale import _, C_, n_

from bibed.gtk import Gtk, Gio, Pango


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

            for status, icon_name in constant_dict.items():
                if icon_name:
                    temp_dict[status] = Gio.ThemedIcon.new(icon_name)
                else:
                    temp_dict[status] = None

            setattr(self, attr_name, temp_dict)

    def setup_treeview_columns(self):

        self.col_key = self.setup_text_column(
            C_('treeview header', 'Key'), BibAttrs.KEY,
            ellipsize=Pango.EllipsizeMode.START,
            attributes={'foreground': BibAttrs.COLOR},
            # tooltip=_('Entry unique key across all databases'),
        )

        self.col_type = self.setup_text_column(
            C_('treeview header', 'Type'), BibAttrs.TYPE,
            attributes={'foreground': BibAttrs.COLOR},
        )

        # DOI column

        # TODO: integrate a pixbuf for 'tags' (keywords) ?

        self.col_file = self.setup_pixbuf_column(
            C_('treeview header', 'F'), BibAttrs.FILE,
            self.get_file_cell_column,
            self.on_file_clicked,
            # tooltip=_('File (PDF)'),
        )
        self.col_url = self.setup_pixbuf_column(
            C_('treeview header', 'U'), BibAttrs.URL,
            self.get_url_cell_column,
            self.on_url_clicked,
            # tooltip=_('URL of entry')
        )
        self.col_quality = self.setup_pixbuf_column(
            C_('treeview header', 'Q'), BibAttrs.QUALITY,
            self.get_quality_cell_column,
            self.on_quality_clicked,
            # tooltip=_('Verified qualify')
        )
        self.col_read = self.setup_pixbuf_column(
            C_('treeview header', 'R'), BibAttrs.READ,
            self.get_read_cell_column,
            self.on_read_clicked,
            # tooltip=_('Read status')
        )
        self.col_comment = self.setup_pixbuf_column(
            C_('treeview header', 'C'), BibAttrs.COMMENT,
            self.get_comment_cell_column,
            # tooltip=_('Personal comment(s)')
        )

        self.col_author = self.setup_text_column(
            _('Author(s)'), BibAttrs.AUTHOR,
            ellipsize=Pango.EllipsizeMode.END,
            attributes={'foreground': BibAttrs.COLOR},
        )
        self.col_title = self.setup_text_column(
            _('Title'), BibAttrs.TITLE, resizable=True,
            ellipsize=Pango.EllipsizeMode.MIDDLE,
            attributes={'foreground': BibAttrs.COLOR},
        )
        self.col_journal = self.setup_text_column(
            _('Journal'), BibAttrs.JOURNAL,
            ellipsize=Pango.EllipsizeMode.END,
            attributes={'foreground': BibAttrs.COLOR},
        )

        self.col_year = self.setup_text_column(
            _('Year'), BibAttrs.YEAR, xalign=1.0,
            attributes={'foreground': BibAttrs.COLOR},
        )

    def on_size_allocate(self, treeview, rectangle):

        self.set_columns_widths(rectangle.width)

    @only_one_when_idle
    def set_columns_widths(self, width):

        # assert lprint_caller_name(levels=4)
        # assert lprint_function_name()

        col_key_width     = round(width * COL_KEY_WIDTH)
        col_type_width    = round(width * COL_TYPE_WIDTH)
        col_author_width  = round(width * COL_AUTHOR_WIDTH)
        col_journal_width = round(width * COL_JOURNAL_WIDTH)
        col_year_width    = round(width * COL_YEAR_WIDTH)

        # col_title_width   = round(width - (
        #     col_key_width + col_author_width
        #     + col_journal_width + col_year_width
        #     + col_type_width
        #     + 5 * COL_PIXBUF_WIDTH
        # ) - COL_SEPARATOR_WIDTH * 10)

        # print(
        #     col_key_width,
        #     col_type_width,
        #     col_author_width,
        #     col_journal_width,
        #     col_year_width,
        #     # col_title_width,
        # )

        self.col_key.set_fixed_width(col_key_width)
        self.col_type.set_fixed_width(col_type_width)
        self.col_author.set_fixed_width(col_author_width)
        self.col_journal.set_fixed_width(col_journal_width)
        self.col_year.set_fixed_width(col_year_width)
        # self.col_title.set_fixed_width(-1)
        # self.col_title.set_min_width(col_title_width - 50)
        # self.col_title.set_max_width(col_title_width + 50)

    # ————————————————————————————————————————————————————————— Pixbufs columns

    def get_read_cell_column(self, col, cell, model, iter, user_data):
        cell.set_property(
            'gicon', self.read_status_pixbufs[
                model.get_value(iter, BibAttrs.READ)])

    def get_quality_cell_column(self, col, cell, model, iter, user_data):
        cell.set_property(
            'gicon', self.quality_status_pixbufs[
                model.get_value(iter, BibAttrs.QUALITY)])

    def get_comment_cell_column(self, col, cell, model, iter, user_data):
        cell.set_property(
            'gicon', self.comment_pixbufs[
                model.get_value(iter, BibAttrs.COMMENT) != ''])

    def get_url_cell_column(self, col, cell, model, iter, user_data):
        cell.set_property(
            'gicon', self.url_pixbufs[
                model.get_value(iter, BibAttrs.URL) != ''])

    def get_file_cell_column(self, col, cell, model, iter, user_data):
        cell.set_property(
            'gicon', self.file_pixbufs[
                model.get_value(iter, BibAttrs.FILE) != ''])

    # ———————————————————————————————————————————————————————— Entry selection

    def get_main_model_iter_by_gid(self, gid):
        ''' '''
        # TODO: use path instead of GID.
        return self.main_model.get_iter(gid)

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

    def get_entries_by_paths(self, paths, with_global_id=False, return_iter=False, only_rows=False):

        # Are we on the list store, or a filter ?
        model   = self.get_model()
        rows    = []
        entries = []

        key_index  = BibAttrs.KEY
        file_index = BibAttrs.FILENAME
        gid_index  = BibAttrs.GLOBAL_ID

        for path in paths:
            treeiter = model.get_iter(path)
            row      = model[treeiter]

            if only_rows:
                rows.append(row)
                continue

            bib_key  = row[key_index]
            filename = row[file_index]

            entry = self.files.get_entry_by_key(bib_key, filename=filename)

            if with_global_id:
                entry.gid = row[gid_index]

            if return_iter:
                entries.append((entry, treeiter, ))

            else:
                entries.append(entry)

        if only_rows:
            return rows

        return entries

    def get_selected_entries(self):
        ''' Used in Gtk.SelectionMode.MULTIPLE. '''

        return self.get_entries_by_paths(
            self.get_selected_rows(paths_only=True),
            with_global_id=True
        )

    # ————————————————————————————————————————————————————————————— Gtk signals

    def on_quality_clicked(self, renderer, path):

        entry = self.get_entry_by_path(path, with_global_id=True)

        entry.toggle_quality()

        # if gpod('bib_auto_save'):
        self.files.trigger_save(entry.database.filename)

    def on_read_clicked(self, renderer, path):

        entry = self.get_entry_by_path(path, with_global_id=True)

        entry.cycle_read_status()

        # if gpod('bib_auto_save'):
        self.files.trigger_save(entry.database.filename)

    def on_url_clicked(self, renderer, path):

        self.open_entries_urls_in_browser(
            [self.get_entry_by_path(path, only_row=True)])

    def on_file_clicked(self, renderer, path):

        self.open_entries_files_in_prefered_application(
            [self.get_entry_by_path(path, only_row=True)])

    def on_treeview_row_activated(self, treeview, path, column):

        # GLOBAL_ID is needed to update the treeview after modifications.
        entry = self.get_entry_by_path(path, with_global_id=True)

        assert(isinstance(entry, BibedEntry))

        return self.window.entry_edit(entry)

    # —————————————————————————————————————————————————————————— “Copy” actions

    def copy_entries_keys_raw_to_clipboard(self, rows=None):
        return self.copy_to_clipboard_or_action(BibAttrs.KEY, rows=rows)

    def copy_entries_keys_formatted_to_clipboard(self, rows=None):
        return self.copy_to_clipboard_or_action(
            BibAttrs.KEY,
            transform_func=BibedEntry.single_bibkey_format,
            rows=rows,
        )

    def copy_entries_urls_to_clipboard(self, rows=None):
        return self.copy_to_clipboard_or_action(BibAttrs.URL, rows=rows)

    def copy_entries_files_to_clipboard(self, rows=None):
        return self.copy_to_clipboard_or_action(BibAttrs.FILE, rows=rows)

    # —————————————————————————————————————————————————————————— “Open” Actions

    def open_entries_urls_in_browser(self, rows=None):
        return self.copy_to_clipboard_or_action(
            BibAttrs.URL,
            action_func=open_urls_in_web_browser,
            action_message='opened in web browser',
            rows=rows,
        )

    def open_entries_files_in_prefered_application(self, rows=None):
        return self.copy_to_clipboard_or_action(
            BibAttrs.FILE,
            action_func=open_with_system_launcher,
            action_message='opened in prefered application',
            rows=rows,
        )

    # —————————————————————————————————————————————————————————— Generic method

    def copy_to_clipboard_or_action(self, field_index, transform_func=None, action_func=None, action_message=None, rows=None):

        if rows is None:
            rows = self.get_selected_rows()
        else:
            rows = rows

        if rows is None:
            self.do_status_change(
                'Nothing selected; nothing copied to clipboard.')
            return

        entry_gids = []
        entry_data = []

        for row in rows:
            entry_gids.append(row[BibAttrs.GLOBAL_ID])
            entry_data.append(row[field_index])

        if bool([x for x in entry_data if x is not None and x.strip() != '']):
            transformed_data = (
                entry_data if transform_func is None
                else transform_func(entry_data)
            )

            if action_func is None:
                final_data = '\n'.join(transformed_data)

                self.clipboard.set_text(final_data, len=-1)

                self.do_status_change(
                    n_(
                        '{data} copied to clipboard (from entry {key}).',
                        '{data} copied to clipboard (from entries {key}).',
                        len(entry_gids),
                    ).format(
                        data=n_(
                            '{} line, {} chars',
                            '{} lines, {} chars',
                            len(transformed_data),
                        ).format(
                            len(transformed_data),
                            len(final_data)
                        ),
                        key=','.join(str(g) for g in entry_gids)))

            else:
                returning_data = action_func(transformed_data)

                self.do_status_change(
                    n_(
                        '“{data}” {message} (from entry {key}).',
                        '“{data}” {message} (from entries {key}).',
                        len(entry_gids),
                    ).format(
                        data=', '.join(returning_data),
                        message=(_('run through {func}').format(
                            func=action_func.__name__)
                            if action_message is None
                            else action_message
                        ),
                        key=', '.join(str(g) for g in entry_gids),
                    )
                )

        else:
            self.do_status_change(
                n_(
                    'Selected entry {key}.',
                    'Selected entries {key}.',
                    len(entry_gids)
                ).format(key=', '.join(str(g) for g in entry_gids)))

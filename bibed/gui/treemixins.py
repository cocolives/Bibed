
from bibed.ltrace import lprint_function_name, lprint_caller_name

from bibed.constants import (
    BibAttrs,
    URL_PIXBUFS,
    FILE_PIXBUFS,
    TYPE_PIXBUFS,
    COMMENT_PIXBUFS,
    READ_STATUS_PIXBUFS,
    QUALITY_STATUS_PIXBUFS,
    COL_KEY_WIDTH,
    COL_TYPE_WIDTH,
    COL_YEAR_WIDTH,
    # COL_PIXBUF_WIDTH,
    COL_AUTHOR_WIDTH,
    COL_IN_OR_BY_WIDTH,
    # COL_SEPARATOR_WIDTH,
)

from bibed.decorators import run_at_most_every, only_one_when_idle
from bibed.utils import (
    open_with_system_launcher,
    open_urls_in_web_browser,
)
from bibed.strings import friendly_filename
from bibed.preferences import gpod
from bibed.controllers import controllers
from bibed.entry import BibedEntry
from bibed.locale import _, C_, n_

from bibed.gtk import Gtk, Gio, Pango
from bibed.gui.helpers import widgets_hide, widgets_show


AUTHOR_COL_TITLE = _('Author(s)')
TITLE_COL_TITLE = _('Title')
IN_OR_BY_COL_TITLE = _('In, by or how')


class BibedEntryTreeViewMixin:
    ''' This class exists only to separate entry-related actions
        from pure-treeview ones. '''

    SELECTION_MODE = Gtk.SelectionMode.MULTIPLE

    def setup_pixbufs(self):

        for attr_name, constant_dict in (
            ('quality_status_pixbufs', QUALITY_STATUS_PIXBUFS),
            ('read_status_pixbufs', READ_STATUS_PIXBUFS),
            ('comment_pixbufs', COMMENT_PIXBUFS),
            ('type_pixbufs', TYPE_PIXBUFS),
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

        self.col_type = self.setup_pixbuf_column(
            'type', C_('treeview header', 'T'), BibAttrs.TYPE,
            self.get_type_cell_column,
            # tooltip=_('Entry type'),
        )

        self.col_key = self.setup_text_column(
            'key', C_('treeview header', 'Key'), BibAttrs.KEY,
            ellipsize=Pango.EllipsizeMode.START,
            attributes={'foreground': BibAttrs.COLOR},
            # tooltip=_('Entry unique key across all databases'),
        )

        # DOI column

        # TODO: integrate a pixbuf for 'tags' (keywords) ?

        self.col_file = self.setup_pixbuf_column(
            'file', C_('treeview header', 'F'), BibAttrs.FILE,
            self.get_file_cell_column, self.on_file_clicked,
            # tooltip=_('File (PDF)'),
        )
        self.col_url = self.setup_pixbuf_column(
            'url', C_('treeview header', 'U'), BibAttrs.URL,
            self.get_url_cell_column, self.on_url_clicked,
            # tooltip=_('URL of entry')
        )
        self.col_quality = self.setup_pixbuf_column(
            'quality', C_('treeview header', 'Q'), BibAttrs.QUALITY,
            self.get_quality_cell_column, self.on_quality_clicked,
            # tooltip=_('Verified qualify')
        )
        self.col_read_status = self.setup_pixbuf_column(
            'read_status', C_('treeview header', 'R'), BibAttrs.READ,
            self.get_read_cell_column, self.on_read_clicked,
            # tooltip=_('Read status')
        )
        self.col_abstract_or_comment = self.setup_pixbuf_column(
            'abstract_or_comment', C_('treeview header', 'C'), BibAttrs.ABSTRACT_OR_COMMENT, self.get_comment_cell_column,
            # tooltip=_('Personal comment(s)')
        )

        self.col_author = self.setup_text_column(
            'author', AUTHOR_COL_TITLE, BibAttrs.AUTHOR,
            ellipsize=Pango.EllipsizeMode.END,
            attributes={'foreground': BibAttrs.COLOR},
        )
        self.col_title = self.setup_text_column(
            'title', TITLE_COL_TITLE, BibAttrs.TITLE, resizable=True,
            ellipsize=Pango.EllipsizeMode.MIDDLE,
            attributes={'foreground': BibAttrs.COLOR},
        )
        self.col_in_or_by = self.setup_text_column(
            'in_or_by', IN_OR_BY_COL_TITLE, BibAttrs.IN_OR_BY,
            ellipsize=Pango.EllipsizeMode.END,
            attributes={'foreground': BibAttrs.COLOR},
        )

        self.col_year = self.setup_text_column(
            'year', _('Year'), BibAttrs.YEAR, xalign=0.9,
            attributes={'foreground': BibAttrs.COLOR},
        )

    @run_at_most_every(125)
    def on_size_allocate(self, treeview, rectangle):

        self.set_columns_widths(rectangle.width)

    def set_columns_widths(self, width=None):

        # assert lprint_caller_name(levels=4)
        # assert lprint_function_name()

        if width is None:
            width = self.get_allocated_width()

        # print('WIDTH', width)

        cols_level1 = (
            self.col_url,
            self.col_file,
            self.col_quality,
            self.col_read_status,
            self.col_abstract_or_comment,
        )

        # self.col_author
        # self.col_year

        if width < 1250:
            widgets_hide([self.col_key])
            multiplicator = 1.0

        if width < 1075:
            widgets_hide([self.col_in_or_by])
            multiplicator = 1.3

        if width < 1025:
            multiplicator = 1.15

        if width < 930:
            widgets_hide(cols_level1)
            multiplicator = 1.5

        if width > 930:
            widgets_show(cols_level1)
            multiplicator = 1.15

        if width > 1025:
            multiplicator = 1.3

        if width > 1075:
            widgets_show([self.col_in_or_by])
            multiplicator = 1.0

        if width > 1250:
            widgets_show([self.col_key])
            multiplicator = 0.9

        col_key_width      = round(width * multiplicator * COL_KEY_WIDTH)
        col_author_width   = round(width * multiplicator * COL_AUTHOR_WIDTH)
        col_in_or_by_width = round(width * multiplicator * COL_IN_OR_BY_WIDTH)
        col_year_width     = round(width * multiplicator * COL_YEAR_WIDTH)

        # col_title_width   = round(width - (
        #     col_key_width + col_author_width
        #     + col_in_or_by_width + col_year_width
        #     + col_type_width
        #     + 5 * COL_PIXBUF_WIDTH
        # ) - COL_SEPARATOR_WIDTH * 10)

        # print(
        #     'key', col_key_width,
        #     'author', col_author_width,
        #     'in_or_by', col_in_or_by_width,
        #     'year', col_year_width,
        #     # 'title', col_title_width,
        # )

        # self.col_title.set_fixed_width(-1)
        # self.col_title.set_min_width(col_title_width - 50)
        # self.col_title.set_max_width(col_title_width + 50)

        self.col_key.set_fixed_width(col_key_width)
        self.col_author.set_fixed_width(col_author_width)
        self.col_in_or_by.set_fixed_width(col_in_or_by_width)
        self.col_year.set_fixed_width(col_year_width)

    # ————————————————————————————————————————————————————————— Pixbufs columns

    def get_type_cell_column(self, col, cell, model, iter, user_data):

        cell.set_property(
            'gicon', self.type_pixbufs[
                model.get_value(iter, BibAttrs.TYPE)
            ]
        )

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
                model.get_value(iter, BibAttrs.ABSTRACT_OR_COMMENT)
            ]
        )

    def get_url_cell_column(self, col, cell, model, iter, user_data):
        cell.set_property(
            'gicon', self.url_pixbufs[
                model.get_value(iter, BibAttrs.URL) != ''])

    def get_file_cell_column(self, col, cell, model, iter, user_data):

        entry_type = model.get_value(iter, BibAttrs.TYPE)
        has_file = model.get_value(iter, BibAttrs.FILE) != ''

        cell.set_property(
            'gicon', self.file_pixbufs.get(
                entry_type if has_file else False,
                self.file_pixbufs['default']
            )
        )

    # ———————————————————————————————————————————————————————— Entry selection

    def get_entry_by_path(self, path, only_row=False):

        return self.get_entries_by_paths([path], only_rows=only_row)[0]

    def get_entries_by_paths(self, paths, return_iter=False, only_rows=False):

        # Are we on the list store, or a filter ?
        model   = self.get_model()
        rows    = []
        entries = []

        key_index  = BibAttrs.KEY
        dbid_index = BibAttrs.DBID

        for path in paths:
            treeiter = model.get_iter(path)
            row      = model[treeiter]

            if only_rows:
                rows.append(row)
                continue

            bib_key = row[key_index]
            dbid = row[dbid_index]

            entry = controllers.files.get_entry_by_key(bib_key, dbid=dbid)

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
        )

    # ————————————————————————————————————————————————————————————— Gtk signals

    def on_query_tooltip(self, widget, x, y, keyboard_tip, tooltip):

        # w, z = self.convert_widget_to_tree_coords(x, y)
        w, z = self.convert_widget_to_bin_window_coords(x, y)

        result = widget.get_path_at_pos(w, z)

        if result is None:
            return False

        path, column, cell_x, cell_y = result

        entry = self.get_entry_by_path(path)

        icon_size = None
        icon_name = None
        markup = None

        if column in (
            self.col_type,
            self.col_key,
            self.col_year,
        ):
            icon_size = Gtk.IconSize.DIALOG
            icon_name = TYPE_PIXBUFS[entry.type]

            markup = (
                '<big>{typee}</big> '
                '<span font="monospace">{key}</span>\n'
                '{title}{year}\n{author}'
            ).format(
                key=entry.key,
                typee=entry.type_label,
                title=entry.col_title,
                author=entry.col_author,
                year=' ({})'.format(entry.col_year) if entry.year else '',
            )

        elif column == self.col_file:

            efile = entry.get_field('file', '')

            if efile != '':
                icon_size = Gtk.IconSize.DIALOG
                icon_name = FILE_PIXBUFS.get(
                    entry.type, FILE_PIXBUFS['default'])

                if entry.type in ('audio', 'music', ):
                    markup_base = _('Play {file}')

                else:
                    markup_base = _('Open {file}')

                markup = markup_base.format(file=friendly_filename(efile))

        elif column == self.col_read_status:

            read_status = entry.col_read_status

            icon_size = Gtk.IconSize.DIALOG
            icon_name = READ_STATUS_PIXBUFS[read_status]

            if read_status == 'read':
                markup = _('You read this entry')

            elif read_status == 'skimmed':
                markup = _('You skimmed this entry')

            else:
                markup = _('Entry is unread')

        elif column == self.col_abstract_or_comment:

            abs_or_com = entry.col_abstract_or_comment

            if abs_or_com is not None:
                icon_size = Gtk.IconSize.DIALOG
                icon_name = COMMENT_PIXBUFS[abs_or_com]

                if abs_or_com == 'both':
                    markup = _('Entry has an abstract and personal comment')

                elif abs_or_com == 'comment':
                    markup = _('Entry has personal comment')

                else:
                    markup = _('Entry has abstract')

        elif column == self.col_title:
            icon_size = Gtk.IconSize.from_name('BIBED_BIG')
            icon_name = TYPE_PIXBUFS[entry.type]
            markup = entry.col_tooltip

        if icon_size:
            tooltip.set_icon_from_icon_name(icon_name, icon_size)
            tooltip.set_markup(markup)
            return True

        return False

    def on_quality_clicked(self, renderer, path):

        entry = self.get_entry_by_path(path)

        entry.toggle_quality()

        if gpod('bib_auto_save'):
            entry.database.write()

    def on_read_clicked(self, renderer, path):

        entry = self.get_entry_by_path(path)

        entry.cycle_read_status()

        if gpod('bib_auto_save'):
            entry.database.write()

    def on_url_clicked(self, renderer, path):

        self.open_entries_urls_in_browser(
            [self.get_entry_by_path(path, only_row=True)])

    def on_file_clicked(self, renderer, path):

        self.open_entries_files_in_prefered_application(
            [self.get_entry_by_path(path, only_row=True)]
        )

    def on_treeview_row_activated(self, treeview, path, column):

        return self.window.entry_edit(
            self.get_entry_by_path(path)
        )

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

        def display_keys(keys):
            lenght = len(keys)
            if lenght == 1:
                return keys[0]

            elif lenght <= limit_keys:
                return ', '.join(str(key) for key in keys)

            else:
                remaining = lenght - limit_keys
                return (
                    ', '.join(str(key) for key in keys[:limit_keys])
                    + ' ' + n_(
                        'and one more',
                        'and {count} more',
                        remaining,
                    ).format(count=remaining)
                )

        if rows is None:
            rows = self.get_selected_rows()
        else:
            rows = rows

        if rows is None:
            self.do_status_change(
                'Nothing selected; nothing copied to clipboard.')
            return

        entry_keys = []
        entry_data = []

        limit_keys = 3

        key_index = BibAttrs.KEY

        for row in rows:
            entry_keys.append(row[key_index])
            entry_data.append(row[field_index])

        if bool([x for x in entry_data if x is not None and x.strip() != '']):
            transformed_data = (
                entry_data if transform_func is None
                else transform_func(entry_data)
            )

            if action_func is None:
                final_data = '\n'.join(transformed_data)

                controllers.clipboard.set_text(final_data, len=-1)

                self.do_status_change(
                    n_(
                        '{data} copied to clipboard (from entry {key}).',
                        '{data} copied to clipboard (from entries {key}).',
                        len(entry_keys),
                    ).format(
                        data=n_(
                            '{} line, {} chars',
                            '{} lines, {} chars',
                            len(transformed_data),
                        ).format(
                            len(transformed_data),
                            len(final_data)
                        ),
                        key=display_keys(entry_keys)
                    )
                )

            else:
                returning_data = action_func(transformed_data)

                self.do_status_change(
                    n_(
                        '“{data}” {message} (from entry {key}).',
                        '“{data}” {message} (from entries {key}).',
                        len(entry_keys),
                    ).format(
                        data=', '.join(returning_data),
                        message=(_('run through {func}').format(
                            func=action_func.__name__)
                            if action_message is None
                            else action_message
                        ),
                        key=display_keys(entry_keys),
                    )
                )

        else:
            self.do_status_change(
                n_(
                    'Selected entry {key}.',
                    'Selected entries {key}.',
                    len(entry_keys)
                ).format(key=display_keys(entry_keys))
            )

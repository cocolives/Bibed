
import logging

# from bibed.foundations import ldebug
from bibed.constants import (
    FileTypes,
    BOXES_BORDER_WIDTH,
    GRID_ROWS_SPACING,
    GRID_COLS_SPACING,
)

# from bibed.exceptions import BibedTreeViewException
# from bibed.preferences import memories  # , gpod
from bibed.gui.helpers import (
    flat_unclickable_button_in_hbox,
    markup_bib_filename,
    widget_call_method,
    widget_properties,
    # add_classes,
)
from bibed.gtk import Gtk, Gio, Dazzle
from bibed.locale import _

# from bibed.gui.renderers import CellRendererTogglePixbuf
# from bibed.gui.treemixins import BibedEntryTreeViewMixin


LOGGER = logging.getLogger(__name__)


class BibedDatabaseListBoxRow(Gtk.ListBoxRow):

    def __init__(self, database, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.database = database


class BibedDatabaseListBox(Gtk.ListBox):

    def __init__(self, application, parent):

        super().__init__()

        self.parent = parent
        self.application = application
        self.all_files = self.application.files

        self.user_files = Dazzle.ListModelFilter.new(self.all_files)
        self.user_files.set_filter_func(self.files_filter_func)

        self.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.set_activate_on_single_click(False)

        self.bind_model(self.user_files, self.create_database_row)

        self.connect('selected-rows-changed', self.on_selected_rows_changed)
        self.connect('row-activated', self.parent.popdown)

    def files_filter_func(self, database, *data):

        return not database.filetype & FileTypes.SYSTEM

    def create_database_row(self, database):

        row = BibedDatabaseListBoxRow(database)

        grid = Gtk.Grid()
        grid.set_column_spacing(GRID_COLS_SPACING)
        grid.set_border_width(BOXES_BORDER_WIDTH)

        label = widget_properties(
            Gtk.Label(),
            expand=True,
            halign=Gtk.Align.START,
        )
        label.set_markup(
            markup_bib_filename(
                database.filename, database.filetype,
                same_size=False, same_line=False)
        )

        button = Gtk.Button()
        icon = Gio.ThemedIcon(name='window-close-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        button.add(image)
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.connect('clicked', self.on_file_close_clicked, database)

        grid.attach(label, 0, 0, 1, 1)
        grid.attach_next_to(button, label, Gtk.PositionType.RIGHT, 1, 1)

        row.add(grid)

        row.show_all()

        return row

    def select_row(self, row):

        row.database.selected = True

        self.unselect_system_databases()

        # Done last to emit the 'selected-rows-changed' as late as possible
        super().select_row(row)

    def unselect_row(self, row):

        row.database.selected = False

        # Done last to emit the 'selected-rows-changed' as late as possible
        super().unselect_row(row)

    def select_all(self):

        self.unselect_system_databases()

        for row in self:
            row.database.selected = True

        # Done last to emit the 'selected-rows-changed' as late as possible
        super().select_all()

    def unselect_all(self):

        for row in self:
            row.database.selected = False

        # Done last to emit the 'selected-rows-changed' as late as possible
        super().unselect_all()

    def select_any(self):

        selected_user = len(tuple(self.all_files.selected_databases))
        selected_system = len(tuple(self.all_files.selected_system_databases))

        if not selected_system:
            if not selected_user:
                self.select_all()

    def update_selected(self):
        ''' Update GUI based on file store selection. '''

        user_selected = tuple(self.all_files.selected_user_databases)
        system_selected = tuple(self.all_files.selected_system_databases)

        if user_selected:
            for row in self:
                if row.database in user_selected:
                    self.select_row(row)
                else:
                    self.unselect_row(row)

        elif system_selected:
            # Toggle the right button, without emitting signal…
            self.parent.sync_system_buttons_states()

        else:
            self.select_all()

    def unselect_system_databases(self):

        for database in self.all_files.system_databases:
            database.selected = False

    def on_file_close_clicked(self, button, database):
        ''' Close current selected file. '''

        # Should we unselect first ?
        # Data store will be cleared anyway.
        # And listbox WILL update the selected_rows() too.

        self.application.close_database(database)
        # self.popdown()

        if self.all_files.num_user:
            self.select_any()

        else:
            self.parent.sync_buttons_states()

    # —————————————————————————————————————————————————————————— System Buttons

    def on_show_system_clicked(self, button, db_name, *data):

        # Unselect other system DBs.
        self.unselect_system_databases()

        getattr(self.all_files, db_name).selected = True

        # unselecting all *after* selecting `db_name` will emit the
        # 'selection-changed' signal, which will be picked up by
        # the rest of the interface.
        # If all user files were already unselected, perhaps
        # another system file was selected. We need to fake a
        # change for interface to react.

        if self.get_selected_rows():
            self.unselect_all()

        else:
            self.emit('selected-rows-changed')

        self.parent.popdown()

    # ——————————————————————————————————————————————————————————————— Selection

    def on_selected_rows_changed(self, *args):

        row_selected_databases = [
            row.database
            for row in self.get_selected_rows()
        ]

        if row_selected_databases:
            system_selected = []

        else:
            # Never forget them, they are not in 'rows'.
            system_selected = list(self.all_files.selected_system_databases)

        self.all_files.sync_selection(row_selected_databases + system_selected)

        # Bubble UP.
        self.application.window.on_selected_files_changed()

    def get_selected_databases(self):

        selected_user = list(self.all_files.selected_databases)

        if selected_user:
            return selected_user

        selected_system = list(self.all_files.selected_system_databases)

        if selected_system:
            return selected_system

        return []


class BibedDatabasePopover(Gtk.Popover):

    def __init__(self, relative_to, *args, **kwargs):

        super().__init__()

        self.application = self.window.application
        self.all_files = self.application.files
        self.data = self.application.data
        self.parent = kwargs.pop('parent')

        self.set_position(Gtk.PositionType.BOTTOM)
        self.set_relative_to(relative_to)

        self.grid = Gtk.Grid()
        # grid.set_column_homogeneous(True)
        self.grid.set_row_spacing(BOXES_BORDER_WIDTH)
        self.grid.set_border_width(BOXES_BORDER_WIDTH)

        self.setup_all_buttons()

        self.setup_listbox()
        # TODO: use self.listbox.drag_highlight_row()
        #       for DND.

        self.setup_system_buttons()

        self.add(self.grid)

        self.sync_buttons_states()

    def popup(self):

        self.show_all()

        self.sync_buttons_states(sync_parent=False)

        super().popup()

        try:
            self.listbox.get_selected_rows()[0].grab_focus()

        except IndexError:

            try:
                self.listbox.get_children()[0].grab_focus()

            except IndexError:
                # No children. Don't bother.
                pass

    def popdown(self, *args):

        super().popdown()

        self.parent.treeview.grab_focus()

    def sync_buttons_states(self, sync_parent=True):

        if not self.is_visible():
            # Window is not ready.
            return

        buttons_all = (
            self.btn_select_all, self.btn_close_all,
        )

        user_file_count = len(self.listbox.user_files)

        widget_call_method(buttons_all,
                           'set_sensitive',
                           bool(user_file_count > 1))

        if user_file_count > 1 and \
                len(self.listbox.get_selected_rows()) == user_file_count:
            self.btn_select_all.set_sensitive(False)

        self.sync_system_buttons_states()

        if sync_parent:
            self.parent.sync_buttons_states(sync_children=False)

    def sync_system_buttons_states(self):

        for button_name in ('trash', 'queue', 'imported', ):

            database = getattr(self.all_files, button_name)
            button = getattr(self, 'btn_show_' + button_name)

            if button.get_active() != database.selected:
                # Block signal to avoid false-positive emissions.
                button.handler_block_by_func(
                    self.listbox.on_show_system_clicked)
                button.set_active(database.selected)
                button.handler_unblock_by_func(
                    self.listbox.on_show_system_clicked)

            button.set_sensitive(bool(len(database)))

    def setup_all_buttons(self):

        grid = widget_properties(
            Gtk.Grid(),
            expand=True,
        )
        grid.set_column_spacing(GRID_COLS_SPACING)

        self.btn_select_all = widget_properties(
            Gtk.Button(), expand=False, halign=Gtk.Align.END,
        )
        icon = Gio.ThemedIcon(name='edit-select-all-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_select_all.add(image)
        self.btn_select_all.set_tooltip_markup(_('Select all files for display.'))
        self.btn_select_all.connect(
            'clicked', self.on_select_all_clicked)

        label_all = widget_properties(
            Gtk.Label(),
            expand=True,
            halign=Gtk.Align.CENTER,
        )

        label_all.set_markup(_('Open databases'))

        self.btn_close_all = widget_properties(
            Gtk.Button(), expand=False, halign=Gtk.Align.END,
        )
        icon = Gio.ThemedIcon(name='window-close-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_close_all.add(image)
        self.btn_close_all.set_tooltip_markup(_('Close all open files.'))
        self.btn_close_all.connect(
            'clicked', self.on_close_all_clicked)

        # add_classes(self.btn_close_all, ['destructive-action'])

        grid.attach(self.btn_select_all, 0, 0, 1, 1)
        grid.attach(label_all, 1, 0, 1, 1)
        grid.attach(self.btn_close_all, 2, 0, 1, 1)

        self.box_all_ops = grid

        self.grid.attach(self.box_all_ops, 0, 0, 1, 1)

    def setup_listbox(self):

        self.listbox = BibedDatabaseListBox(
            application=self.application, parent=self)

        self.grid.attach_next_to(
            self.listbox,
            self.box_all_ops,
            Gtk.PositionType.BOTTOM,
            1, 1
        )

    def setup_system_buttons(self):

        grid = Gtk.Grid()
        grid.set_column_spacing(BOXES_BORDER_WIDTH)

        self.btn_show_trash = Gtk.ToggleButton()
        self.btn_show_trash.add(flat_unclickable_button_in_hbox(
            'trash', _('Trash'),
            icon_name='user-trash-full-symbolic',
            border=False,
        ))
        self.btn_show_trash.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_show_trash.connect(
            'clicked', self.listbox.on_show_system_clicked, 'trash')

        self.btn_show_queue = Gtk.ToggleButton()
        self.btn_show_queue.add(flat_unclickable_button_in_hbox(
            'queue', _('Queue'),
            icon_name='view-list-symbolic',
            border=False,
        ))
        self.btn_show_queue.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_show_queue.connect(
            'clicked', self.listbox.on_show_system_clicked, 'queue')

        # user-bookmarks-symbolic
        self.btn_show_imported = Gtk.ToggleButton()
        self.btn_show_imported.add(flat_unclickable_button_in_hbox(
            'imported', _('Imported'),
            icon_name='emblem-ok-symbolic',
            border=False,
        ))
        self.btn_show_imported.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_show_imported.connect(
            'clicked', self.listbox.on_show_system_clicked, 'imported')

        # box.pack_start(self.btn_show_queue, True, False, 0)
        # box.pack_start(self.btn_show_imported, True, False, 0)
        grid.attach(self.btn_show_trash, 0, 0, 1, 1)

        self.grid_system = grid

        self.grid.attach_next_to(
            self.grid_system,
            self.listbox,
            Gtk.PositionType.BOTTOM,
            1, 1)

    def on_select_all_clicked(self, button, *data):

        self.listbox.select_all()

    def on_close_all_clicked(self, button, *data):
        ''' Close current selected file. '''

        for database in tuple(self.all_files.user_databases):
            self.application.close_database(database)

        self.sync_buttons_states()

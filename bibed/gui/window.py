import os
import logging

from bibed.foundations import (
    lprint, ldebug,
    lprint_function_name,
    lprint_caller_name,
)

from bibed.constants import (
    APP_NAME,
    # BibAttrs,
    FSCols,
    FileTypes,
    # BIBED_ICONS_DIR,
    # SEARCH_WIDTH_NORMAL,
    SEARCH_WIDTH_EXPANDED,
    COMBO_CHARS_DIVIDER,
    RESIZE_SIZE_MULTIPLIER,
    BIBED_ASSISTANCE_FR,
    BIBED_ASSISTANCE_EN,
)

from bibed.preferences import memories, gpod
from bibed.utils import get_user_home_directory, friendly_filename
from bibed.entry import BibedEntry

from bibed.gui.helpers import (
    flash_field,
    markup_bib_filename,
    markup_entries,
    add_classes,
    remove_classes,
    message_dialog,
    widget_properties,
    label_with_markup,
    flat_unclickable_button_in_hbox,
)
from bibed.gui.preferences import BibedPreferencesDialog
from bibed.gui.database import BibedDatabasePopover
from bibed.gui.treeview import BibedMainTreeView
from bibed.gui.search import BibedSearchBar
from bibed.gui.entry_type import BibedEntryTypeDialog
from bibed.gui.entry import BibedEntryDialog
from bibed.gui.dialogs import BibedMoveDialog
from bibed.gtk import Gio, GLib, Gtk, Gdk, Pango


LOGGER = logging.getLogger(__name__)


class BibedWindowBlockSignalsContextManager:
    def __init__(self, window):
        self.win = window

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.win.unblock_signals()


class BibedWindow(Gtk.ApplicationWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_name('Bibed')

        # This will be in the windows group and have the "win" prefix
        max_action = Gio.SimpleAction.new_stateful(
            "maximize", None, GLib.Variant.new_boolean(False))
        max_action.connect("change-state", self.on_maximize_toggle)
        self.add_action(max_action)

        # Keep it in sync with the actual state
        self.connect("notify::is-maximized",
                     lambda obj, pspec: max_action.set_state(
                         GLib.Variant.new_boolean(obj.props.is_maximized)))

        self.connect('check-resize', self.on_resize)
        self.connect('key-press-event', self.on_key_pressed)

        self.setup_icon()

        # TODO: use gui.helpers.get_screen_resolution()
        dimensions = (1200, 600)

        if gpod('remember_windows_states'):
            remembered_dimensions = memories.main_window_dimensions

            if remembered_dimensions is not None:
                dimensions = remembered_dimensions

        # TODO: check dimensions are not > screen_size, then lower them.
        #       20190129: I've had a 23487923 pixels windows which made
        #       Bibed crash at startup, don't know how nor why.

        self.set_default_size(*dimensions)

        # keep for resize() operations smothing.
        self.current_size = dimensions

        # self.set_border_width(10)

        # prepared for future references.
        self.preferences_dialog = None

        # ———————————————————————————————————————————————————————— BibEd Window

        self.application = kwargs['application']

        self.setup_treeview()
        self.setup_network()

        self.setup_searchbar()
        self.setup_stack()

        self.setup_headerbar()
        self.setup_statusbar()

        self.setup_vbox()

    def setup_icon(self):

        # icon_filename = os.path.join(
        #     BIBED_ICONS_DIR, 'gnome-contacts.png')
        # LOGGER.debug('loading Window icon from {}'.format(icon_filename))

        self.set_icon_name('gnome-contacts')
        self.set_default_icon_name('gnome-contacts')
        # self.set_icon_from_file(icon_filename)
        # self.set_default_icon_from_file(icon_filename)

        # pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_filename)
        # self.set_default_icon_list([pixbuf])
        # self.set_icon_list([pixbuf])
        pass

    def setup_searchbar(self):

        # used to speed up title updates during searches.
        self.matched_files = set()

        self.search = Gtk.SearchEntry()

        self.search.props.width_chars = SEARCH_WIDTH_EXPANDED
        self.search.connect('search-changed',
                            self.on_search_filter_changed)

        self.searchbar = BibedSearchBar(self.search)

    def setup_stack(self):

        stack = Gtk.Stack()

        stack.set_transition_type(
            Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        stack.set_transition_duration(500)

        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(stack)

        stack.add_titled(
            self.treeview_sw,
            'database',
            'BIB Databases'
        )

        stack.child_set_property(
            self.treeview_sw, 'icon-name',
            'accessories-dictionary-symbolic')

        stack.add_titled(
            self.lbl_network,
            'network',
            '{app} network'.format(app=APP_NAME)
        )

        stack.child_set_property(
            self.lbl_network, 'icon-name',
            'network-workgroup-symbolic')
        # 'utilities-system-monitor-symbolic'

        self.stack_switcher = stack_switcher
        self.stack = stack

    def setup_vbox(self):
        self.vbox = Gtk.VBox()

        self.vbox.pack_start(self.searchbar, False, True, 0)
        self.vbox.pack_start(self.stack, True, True, 0)
        self.vbox.pack_end(self.statusbar, False, True, 0)

        self.add(self.vbox)

    def setup_statusbar(self):

        self.statusbar = Gtk.Statusbar()

        # its context_id - not shown in the UI but needed
        # to uniquely identify the source of a message
        self.context_id = self.statusbar.get_context_id("example")

        self.do_status_change("Ready. Waiting for action…")

    def setup_headerbar(self):

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        self.set_titlebar(hb)

        # This is to connect the headerbar close button to our quit method.
        self.connect('delete-event', self.application.on_quit)

        # ———————————————————————— Left side, from start to end

        bbox_file = widget_properties(
            Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL),
            # classes=['linked'],
        )

        self.btn_file_new = Gtk.Button()
        self.btn_file_new.set_tooltip_markup('Create an empty BIB database')
        self.btn_file_new.connect('clicked', self.on_file_new_clicked)
        icon = Gio.ThemedIcon(name='document-new-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_file_new.add(image)
        self.btn_file_new.set_relief(Gtk.ReliefStyle.NONE)

        bbox_file.add(self.btn_file_new)

        self.btn_file_open = Gtk.Button()
        self.btn_file_open.set_tooltip_markup('Open an existing BIB database')
        self.btn_file_open.connect('clicked', self.on_file_open_clicked)
        icon = Gio.ThemedIcon(name='document-open-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_file_open.add(image)
        self.btn_file_open.set_relief(Gtk.ReliefStyle.NONE)

        bbox_file.add(self.btn_file_open)

        hb.pack_start(bbox_file)

        # object-select-symbolic
        self.btn_file_select = Gtk.Button()
        self.btn_file_select.set_tooltip_markup('Select databases to display in main view')
        self.btn_file_select.add(flat_unclickable_button_in_hbox(
            'file_select', 'Databases',
            icon_name='drive-multidisk-symbolic',
        ))

        self.files_popover = BibedDatabasePopover(
            self.btn_file_select, window=self)

        self.btn_file_select.connect('clicked',
                                     self.on_file_select_clicked,
                                     self.files_popover)

        # bbox_file.add(self.btn_file_select)
        hb.pack_start(self.btn_file_select)

        bbox_entry = widget_properties(
            Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL),
            classes=['linked'],
        )

        self.btn_add = Gtk.Button()
        self.btn_add.set_tooltip_markup('Add a bibliography entry')
        icon = Gio.ThemedIcon(name='list-add-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_add.add(image)
        self.btn_add.connect('clicked', self.on_entry_add_clicked)

        bbox_entry.add(self.btn_add)

        self.btn_move = Gtk.Button()
        self.btn_move.set_tooltip_markup('Move selected entries to another database')
        icon = Gio.ThemedIcon(name='go-next-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_move.add(image)
        self.btn_move.connect('clicked', self.on_entries_move_clicked)

        bbox_entry.add(self.btn_move)

        self.btn_delete = Gtk.Button()  # edit-delete-symbolic
        self.btn_delete.set_tooltip_markup('Trash or delete selected entries')
        icon = Gio.ThemedIcon(name='list-remove-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_delete.add(image)
        self.btn_delete.connect('clicked', self.on_entries_delete_clicked)

        bbox_entry.add(self.btn_delete)

        hb.pack_start(bbox_entry)

        # ————————————————————————————— Right side, from end to start

        self.btn_preferences = Gtk.Button()
        self.btn_preferences.set_tooltip_markup('Show application preferences')
        icon = Gio.ThemedIcon(name='preferences-system-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_preferences.add(image)
        self.btn_preferences.connect(
            'clicked', self.on_preferences_clicked)

        hb.pack_end(self.btn_preferences)

        hb.pack_end(self.stack_switcher)

        self.btn_search = Gtk.Button()
        self.btn_search.set_tooltip_markup('Start searching in selected databases')
        icon = Gio.ThemedIcon(name='system-search-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_search.add(image)
        self.btn_search.connect('clicked', self.on_search_clicked)

        hb.pack_end(self.btn_search)

        self.headerbar = hb

    def setup_network(self):

        self.lbl_network = widget_properties(
            label_with_markup(
                '<big>Bibed Network</big>\n\n'
                'Upcoming feature. Please wait.\n'
                '(You have no choice, anyway :-D)\n'
                'Come discuss it: '
                '<a href="{discuss_en}">in english</a> '
                '| <a href="{discuss_fr}">in french</a>'.format(
                    discuss_en=BIBED_ASSISTANCE_EN,
                    discuss_fr=BIBED_ASSISTANCE_FR,
                ),
                name='network',
                xalign=0.5,
                yalign=0.5,
            ),
            expand=True,
        )

    def setup_treeview(self):

        self.treeview_sw = Gtk.ScrolledWindow()
        self.treeview_sw.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC
        )

        # For CSS.
        self.treeview_sw.set_name('main')

        self.treeview = BibedMainTreeView(
            model=self.application.data,
            application=self.application,
            clipboard=self.application.clipboard,
            window=self,
        )

        self.treeview.selection.connect(
            'changed', self.on_treeview_selection_changed)

        self.treeview_sw.add(self.treeview)

    def update_title(self):

        # assert lprint_caller_name(levels=5)
        # assert lprint_function_name()

        # This will automatically count or exclude user or system files,
        # because this points either to the TreeModelFilter or the main model.
        row_count = len(self.treeview.get_model())

        active_files = self.get_selected_filenames(with_type=True)
        active_files_count = len(active_files)

        if active_files_count > 1:
            pass

        if active_files_count == self.application.files.num_user:
            # All user files are selected.

            search_text = self.get_search_text()

            if search_text:
                # We have to gather files count from
                # current global filter results.

                files_count = len(self.matched_files)

            else:
                files_count = self.application.files.num_user

        else:
            files_count = active_files_count

        if active_files:
            title_value = '{0} – {1}'.format(
                APP_NAME,
                friendly_filename(active_files[0][0])
                if active_files_count == 1
                else '{} files selected'.format(active_files_count)
            )

        else:
            if self.application.files.num_user:
                title_value = '{0} – NO FILE SELECTED'.format(APP_NAME)

            else:
                title_value = '{0} – Welcome!'.format(APP_NAME)

        subtitle_value = '{0} item{1} in {2} file{3}'.format(
            row_count,
            's' if row_count > 1 else '',
            files_count,
            's' if files_count > 1 else '',
        )

        self.headerbar.props.title = title_value
        self.headerbar.props.subtitle = subtitle_value

        assert ldebug('update_title() to {0} and {1}.'.format(
                      title_value, subtitle_value))

    def sync_buttons_states(self, sync_children=True, *args, **kwargs):
        ''' Hide or disable relevant widgets, determined by context.

            This method is called either “as-is” (without argument) by
            application, or with arguments by connected signalsself.
            In both cases we don't use arguments, and re-determine the
            context from scratch.

        '''

        # assert lprint_caller_name(levels=5)

        how_many_files = self.application.files.num_user

        widgets_to_change = (
            # file-related buttons
            self.btn_file_select,
            # TODO: insert popover buttons here,
            #       or forward state to popover.

            # Entry-related buttons.
            self.btn_add, self.btn_move, self.btn_delete,
        )

        if how_many_files:
            for widget in widgets_to_change:
                widget.show()

        else:
            for widget in widgets_to_change:
                widget.hide()

        if sync_children:
            self.files_popover.sync_buttons_states(sync_parent=False)

        # TODO: WHY THIS ?
        # self.on_treeview_selection_changed()

    def entry_selection_buttons_set_sensitive(self, is_sensitive):

        for button in (self.btn_move, self.btn_delete, ):
            button.set_sensitive(is_sensitive)

    # ———————————————————————————————————————————————————————————— “ON” actions

    def on_treeview_selection_changed(self, *args, **kwargs):

        self.entry_selection_buttons_set_sensitive(
            bool(self.treeview.get_selected_rows())
        )

    def on_maximize_toggle(self, action, value):

        action.set_state(value)

        if value.get_boolean():
            self.maximize()
        else:
            self.unmaximize()

        self.on_resize(self)

    def on_resize(self, window):

        previous_width, previous_height = self.current_size
        current_width, current_height = self.get_size()

        if previous_width == current_width:
            # Avoid resize infinite loops.
            return

        # Keep in memory for next resize.
        self.current_size = (current_width, current_height)

        if gpod('remember_windows_states'):
            memories.main_window_dimensions = self.current_size

        # self.cmb_files_renderer.props.max_width_chars = (
        #     current_width * RESIZE_SIZE_MULTIPLIER / COMBO_CHARS_DIVIDER
        # )
        # self.cmb_files.set_size_request(
        #     current_width * RESIZE_SIZE_MULTIPLIER, -1)
        # self.cmb_files.queue_resize()

        self.treeview.set_columns_widths(current_width)

    def on_search_filter_changed(self, entry):
        ''' Signal: chain the global filter method. '''

        self.do_filter_data_store()

    def on_selected_files_changed(self, *args):
        ''' Signal: chain the global filter method. '''

        # assert lprint_caller_name(levels=5)
        # assert lprint_function_name()

        self.do_filter_data_store()

        # TODO: remove call if not needed anymore.
        self.sync_buttons_states()

        # In case there is a search in progress, focus the field to make
        # the user notice why she could be seeing nothing (like empty file).
        if self.get_search_text():
            flash_field(self.search)

    def on_key_pressed(self, widget, event):

        search_result = self.searchbar.handle_event(event)

        if search_result:
            return True

        # get search context
        search_text = self.search.get_text().strip()

        keyval = event.keyval
        # state = event.state

        # TODO: convert all of these to proper accels.
        #       See  http://gtk.10911.n7.nabble.com/GdkModifiers-bitmask-and-GDK-SHIFT-MASK-question-td4404.html
        #       And https://stackoverflow.com/a/10890393/654755
        #       Control+Shift-u → Control+U
        #

        # check the event modifiers (can also use SHIFTMASK, etc)
        ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)
        # shift = (event.state & Gdk.ModifierType.SHIFT_MASK)
        ctrl_shift = (
            event.state & (Gdk.ModifierType.CONTROL_MASK
                           | Gdk.ModifierType.SHIFT_MASK)
        )

        # Alternative way of knowing key pressed.
        # keyval_name = Gdk.keyval_name(keyval)
        # if ctrl and keyval_name == 's':

        if ctrl and keyval == Gdk.KEY_c:
            self.treeview.copy_entries_keys_formatted_to_clipboard()

        if ctrl and keyval == Gdk.KEY_k:
            self.treeview.copy_entries_keys_raw_to_clipboard()

        elif ctrl and keyval == Gdk.KEY_u:

            if gpod('url_action_opens_browser'):
                self.treeview.open_entries_urls_in_browser()
            else:
                self.treeview.copy_entries_urls_to_clipboard()

        elif ctrl_shift and keyval == Gdk.KEY_U:
            # NOTE: the upper case 'U'

            if gpod('url_action_opens_browser'):
                self.treeview.copy_entries_urls_to_clipboard()
            else:
                self.treeview.open_entries_urls_in_browser()

        elif ctrl_shift and keyval == Gdk.KEY_T:

            self.treeview.switch_tooltips()

        elif ctrl and keyval == Gdk.KEY_s:

            if gpod('bib_auto_save'):
                # propagate signal, we do not need to save.
                return True

            LOGGER.info('Control-S pressed (no action yet).')

            # TODO: save selected files.

        elif ctrl and keyval == Gdk.KEY_r:

            # keep memory, in case file order change during reload.
            selected_databases = tuple(self.application.files.selected_databases)

            with self.block_signals():
                # Don't let combo change and update “memories” while we
                # just reload files to attain same conditions as now.
                self.application.reload_files(
                    'Reloaded all open files at user request.')

            # restore memory / session
            self.set_selected_databases(selected_databases)

            self.do_activate()

        elif ctrl_shift and keyval == Gdk.KEY_R:
            # NOTE: the upper case 'R'

            self.application.reload_css_provider_data()

        elif ctrl and keyval == Gdk.KEY_Page_Down:
            # switch file next
            pass

        elif ctrl and keyval == Gdk.KEY_Page_Up:
            # switch file previous
            pass

        elif ctrl and keyval == Gdk.KEY_f:
            self.searchbar.set_search_mode(True)

        elif ctrl and keyval == Gdk.KEY_comma:
            self.btn_preferences.emit('clicked')

        elif ctrl and keyval == Gdk.KEY_l:
            self.btn_file_select.emit('clicked')

        elif ctrl and keyval == Gdk.KEY_m:
            if self.application.files.num_user:
                self.btn_move.emit('clicked')

        elif ctrl and keyval == Gdk.KEY_n:
            if self.application.files.num_user:
                self.btn_add.emit('clicked')

        elif not ctrl and keyval == Gdk.KEY_Delete:
            self.btn_delete.emit('clicked')

        elif ctrl and keyval == Gdk.KEY_o:
            self.btn_file_open.emit('clicked')

        elif ctrl and keyval == Gdk.KEY_w:

            for database in tuple(
                    self.application.files.selected_user_databases):
                self.application.close_file(database.filename)

        elif search_text and (
            keyval in (Gdk.KEY_Down, Gdk.KEY_Up) or (
                ctrl and keyval in (Gdk.KEY_j, Gdk.KEY_k)
            )
        ):
            # we limit on search_text, else we grab the genuine
            # up/down keys already handled by the treeview.

            # TODO: refactor this block and create
            #       treeview.select_next() and treeview.select_previous()
            select = self.treeview.get_selection()
            model, treeiter = select.get_selected()

            # Here we iterate through the SORTER,
            # (first level under the TreeView),
            # not the filter. This is INTENDED.
            # It doesn't work on the filter.
            store = self.application.sorter

            if keyval in (Gdk.KEY_j, Gdk.KEY_Down):

                if treeiter is not None:
                    select.unselect_iter(treeiter)
                    treeiter_next = store.iter_next(treeiter)

                    if treeiter_next is None:
                        # We hit last row.
                        treeiter_next = treeiter

                else:
                    treeiter_next = store[0].iter

            else:
                # Key up / Control-K (backward)

                if treeiter is not None:
                    select.unselect_iter(treeiter)
                    treeiter_next = store.iter_previous(treeiter)

                    if treeiter_next is None:
                        # We hit first row.
                        treeiter_next = treeiter
                else:
                    treeiter_next = store[-1].iter

            select.select_iter(treeiter_next)

        elif not ctrl and keyval == Gdk.KEY_Escape:

            # TODO: if self.search.has_focus():
            #       even if no search_text, Just refocus
            #       the treeview without resetting files.

            if search_text:
                self.search.set_text('')

                try:
                    del memories.search_text

                except Exception:
                    pass

                if self.searchbar.get_search_mode():
                    self.searchbar.set_search_mode(False)

            elif self.searchbar.get_search_mode():
                self.searchbar.set_search_mode(False)

            else:

                rows = self.treeview.get_selected_rows()

                if rows not in (None, []):
                    self.treeview.unselect_all()

                else:
                    application_files = self.application.files
                    selected_user_databases = tuple(
                        application_files.selected_user_databases)

                    if len(selected_user_databases) \
                            != application_files.num_user:
                        self.files_popover.listbox.select_all()

            self.treeview.grab_focus()

        else:
            # The keycode combination was not handled, propagate.
            return False

        # Stop propagation of signal, we handled it.
        return True

    # ——————————————————————————————————————————————————————————— Files buttons

    def on_file_new_clicked(self, button):
        ''' Create a new file. '''

        dialog = Gtk.FileChooserDialog(
            "Please create a new BIB file", self,
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        dialog.set_current_name('Untitled bibliography.bib')
        dialog.set_current_folder(
            gpod('working_folder') or get_user_home_directory())

        dialog.add_filter(self.get_bib_filter())

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            self.application.create_file(dialog.get_filename())

        elif response == Gtk.ResponseType.CANCEL:
            pass

        dialog.destroy()

    def on_file_open_clicked(self, widget):

        dialog = Gtk.FileChooserDialog(
            "Please choose a BIB file", self,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        dialog.set_current_folder(
            gpod('working_folder') or get_user_home_directory())

        dialog.set_select_multiple(True)
        dialog.add_filter(self.get_bib_filter())

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            # dialog.set_select_multiple(False)
            # self.application.open_file(dialog.get_filename())
            filenames = dialog.get_filenames()
            databases_to_select = []

            # Same problem as in app.do_activate(): when loading more than two
            # files, only the two first fire a on_*changed() signal. Thus we
            # block everything, and compute things manually after load.
            with self.block_signals():
                for filename in filenames:
                    databases_to_select.append(
                        self.application.open_file(filename, recompute=False)
                    )

            self.treeview.main_model.do_recompute_global_ids()
            self.set_selected_databases(databases_to_select)

            self.do_activate()

        elif response == Gtk.ResponseType.CANCEL:
            pass

        dialog.destroy()

    def on_file_select_clicked(self, button, popover):

        if popover.is_visible():
            popover.popdown()

        else:
            popover.popup()

    # ——————————————————————————————————————————————————————————— Entry buttons

    def on_entry_add_clicked(self, button):

        entry_add_dialog = BibedEntryTypeDialog(parent=self)
        response = entry_add_dialog.run()

        if response == Gtk.ResponseType.OK:
            entry_type = entry_add_dialog.get_entry_type()

            entry_add_dialog.hide()

            entry = BibedEntry.new_from_type(entry_type)

            entry_edit_dialog = BibedEntryDialog(
                parent=self, entry=entry)

            response = entry_edit_dialog.run()

            if response:
                # Update the number of entries if relevant.
                self.update_title()

                self.do_status_change(
                    '{entry} added to {database}.'.format(
                        entry=response, database=os.path.basename(response.database.filename)))

            entry_edit_dialog.destroy()

        entry_add_dialog.destroy()

    def on_entries_move_clicked(self, button):

        selected_entries = self.treeview.get_selected_entries()

        if selected_entries is None:
            return

        destination, moved_count, unchanged_count = BibedMoveDialog(
            self, selected_entries, self.application.files).run()

        if destination and moved_count > 0:
            self.do_status_change(
                '{count} entries moved to {destination}{unchanged}.'.format(
                    count=len(selected_entries), destination=destination,
                    unchanged=', {count} already there'.format(unchanged_count)
                    if unchanged_count else ''))

    def on_entries_delete_clicked(self, button):

        use_trash = gpod('use_trash')

        selected_entries = self.treeview.get_selected_entries()

        if selected_entries is None:
            return

        trashed_entries = []

        # Copy, else “changed during iteration” occurs, but for an
        # unknown reason it does not produce any error, and gets
        # unnoticed (and some entries are not processed…).
        for entry in selected_entries[:]:
            if entry.is_trashed:
                trashed_entries.append(entry)
                selected_entries.remove(entry)

        if selected_entries:
            if use_trash:
                self.application.files.trash_entries(selected_entries)

            else:
                self.ask_and_delete_entries(selected_entries)

            self.do_status_change('{count} entries {what}.'.format(
                count=len(selected_entries),
                what='trashed' if use_trash else 'definitively deleted'))

        if trashed_entries:
            self.ask_and_delete_entries(trashed_entries, trashed=True)

            self.do_status_change(
                '{count} previously trashed entries '
                'definitively deleted.'.format(
                    count=len(trashed_entries)))

    def ask_and_delete_entries(self, selected_entries, trashed=False):

        def delete_callback(selected_entries):
            databases_to_write = set()

            for entry in selected_entries:
                databases_to_write.add(entry.database)
                entry.delete(write=False)

            for database in databases_to_write:
                database.write()

            self.do_filter_data_store()

        entries_count = len(selected_entries)

        if entries_count > 1:
            if trashed:
                title = 'Wipe {count} entries from trash?'.format(
                    count=entries_count)
            else:
                title = 'Delete {count} entries?'.format(count=entries_count)

            entries_list = markup_entries(selected_entries, entries_count)

            secondary_text = (
                'This will permanently delete the following entries:\n'
                '{entries_list}\n from your database(s).'.format(
                    entries_list=entries_list
                )
            )
        else:
            entry = selected_entries[0]
            title = 'Delete entry?'
            secondary_text = (
                'This will permanently delete {entry} from your database.'.format(
                    entry=entry.short_display
                )
            )

        secondary_text += '\n\nThis action cannot be undone. Are you sure?'

        message_dialog(
            self, Gtk.MessageType.WARNING,
            title, secondary_text,
            delete_callback, selected_entries
        )

    # ——————————————————————————————————————————————————————————— Other buttons

    def on_search_clicked(self, button):

        self.searchbar.set_search_mode(
            not self.searchbar.get_search_mode())

    def on_preferences_clicked(self, button):

        if self.preferences_dialog:
            self.preferences_dialog.run()

        else:
            self.preferences_dialog = BibedPreferencesDialog(self)
            self.preferences_dialog.run()
        # response = dialog.run()

        # if response == Gtk.ResponseType.OK:
        #     LOGGER.info("The OK button was clicked")

        self.preferences_dialog.hide()
        self.preferences_dialog.destroy()
        self.preferences_dialog = None

    # ————————————————————————————————————————————————————————————— GET proxies

    def get_bib_filter(self):

        filter_bib = Gtk.FileFilter()
        filter_bib.set_name('Bib(La)Tex files')
        filter_bib.add_pattern('*.bib')

        return filter_bib

    def get_selected_filenames(self, with_type=False):

        selected_databases = tuple(self.application.files.selected_databases)

        if with_type:
            return [
                (database.filename, database.filetype, )
                for database in selected_databases
            ]

        return [
            database.filename
            for database in selected_databases
        ]

    def set_selected_databases(self, databases_to_select):

        self.application.files.sync_selection(databases_to_select)

        self.files_popover.listbox.update_selected()

    def get_search_text(self):

        return self.search.get_text().strip()

    # ————————————————————————————————————————————————————————— Signal blocking

    def block_signals(self):
        ''' This function can be used as context manager or not. '''

        self.files_popover.listbox.handler_block_by_func(
            self.files_popover.listbox.on_selected_rows_changed)

        return BibedWindowBlockSignalsContextManager(self)

    def unblock_signals(self):

        self.files_popover.listbox.handler_unblock_by_func(
            self.files_popover.listbox.on_selected_rows_changed)

        pass

    # —————————————————————————————————————————————————————————————— DO actions

    def do_activate(self):

        self.update_title()
        self.sync_buttons_states()
        self.treeview.do_column_sort()

    def do_status_change(self, message):
        self.statusbar.push(
            self.context_id, message)

    def do_filter_data_store(self):
        ''' Filter the data store on filename, search_text, or both. '''

        # assert lprint_caller_name(levels=2)
        # assert lprint_function_name()

        selected_filenames = tuple(
            x.filename for x in self.application.files.selected_databases
        )

        if selected_filenames:
            # Should we sort them first ?
            if memories.selected_filenames != selected_filenames:
                memories.selected_filenames = selected_filenames

        else:
            if memories.selected_filenames is not None:
                del memories.selected_filenames

        search_text = self.get_search_text()

        if search_text:
            if memories.search_text != search_text:
                memories.search_text = search_text
        else:
            if memories.search_text is not None:
                del memories.search_text

        def refilter():
            self.matched_files = set()
            self.treeview.set_model(self.application.sorter)
            self.application.filter.refilter()

        if (':' in search_text and len(search_text) > 3) \
                or (':' not in search_text and len(search_text) > 1):
            refilter()

        else:
            refilter()

        self.update_title()

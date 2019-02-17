
import logging

from bibed.exceptions import NoDatabaseForFilenameError

from bibed.ltrace import (  # NOQA
    ldebug, lprint,
    lprint_caller_name,
    lprint_function_name,
)

from bibed.constants import (
    APP_NAME,
    BIBED_ASSISTANCE_FR,
    BIBED_ASSISTANCE_EN,
)

from bibed.decorators import run_at_most_every, only_one_when_idle
from bibed.locale import _, n_
from bibed.preferences import memories, gpod
from bibed.user import get_user_home_directory
from bibed.strings import friendly_filename
from bibed.entry import BibedEntry

from bibed.gtk import Gio, GLib, Gtk, Gdk

from bibed.gui.stack import BibedStack
from bibed.gui.helpers import (
    get_screen_size,
    flash_field,
    markup_entries,
    message_dialog,
    widget_properties,
    widgets_show,
    widgets_hide,
    widget_replace,
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

        self.set_name(APP_NAME)

        # This will be in the windows group and have the "win" prefix
        self.action_maximize = Gio.SimpleAction.new_stateful(
            'maximize', None, GLib.Variant.new_boolean(False))
        self.add_action(self.action_maximize)

        self.setup_icon()

        # prepared for future references.
        self.preferences_dialog = None

        self.application = kwargs['application']

        was_maximized = self.setup_dimensions()

        self.setup_treeview()
        self.setup_booked()

        self.setup_searchbar()
        self.setup_stack()

        self.setup_headerbar()
        self.setup_statusbar()

        self.setup_vbox()

        self.action_maximize.connect('change-state', self.on_maximize_toggle)
        self.connect('window-state-event', self.on_window_state_changed)

        self.connect('check-resize', self.on_resize)
        self.connect('key-press-event', self.on_key_pressed)

        self.set_default_size(*self.current_size)

        if was_maximized:
            self.on_maximize_toggle(self.action_maximize, True)

    def setup_dimensions(self):

        was_maximized = False
        monitor_dimensions = get_screen_size(self)

        # This is a start, in case everything fails.
        dimensions = [int(d * 0.8) for d in monitor_dimensions]

        if gpod('remember_windows_states'):

            is_maximized = memories.main_window_is_maximized

            if is_maximized is not None and is_maximized:
                was_maximized = True

            remembered_dimensions = memories.main_window_dimensions

            if remembered_dimensions is not None:
                dimensions = remembered_dimensions

        # 20190129: I've been given a 23487923 pixels windows which made
        # Bibed crash in wayland at startup, don't know how nor why.

        if dimensions[0] > monitor_dimensions[0]:
            dimensions = [monitor_dimensions[0] * 0.8, dimensions[1]]

        if dimensions[1] > monitor_dimensions[1]:
            dimensions = (dimensions[0], monitor_dimensions[1] * 0.8)

        # keep for resize() operations smothing.
        self.current_size = dimensions

        return was_maximized

    def setup_icon(self):

        self.set_icon_name('bibed-logo')
        self.set_default_icon_name('bibed-logo')

    def setup_searchbar(self):

        # used to speed up title updates during searches.
        self.matched_databases = set()

        self.search = Gtk.SearchEntry()

        self.search.connect('search-changed',
                            self.on_search_filter_changed)

        self.searchbar = BibedSearchBar(self.search, self.treeview)

    def setup_stack(self):

        stack = BibedStack(self)

        stack.set_transition_type(
            Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        stack.set_transition_duration(500)

        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(stack)

        stack.add_titled(
            self.treeview_sw,
            'bibed',
            _('bibliography assistant')
        )

        stack.child_set_property(
            self.treeview_sw, 'icon-name',
            'drive-multidisk-symbolic')

        stack.add_titled(
            self.lbl_booked,
            'booked',
            _('Upcoming feature').format(app=APP_NAME)
        )

        stack.child_set_property(
            self.lbl_booked, 'icon-name',
            'accessories-dictionary-symbolic')
        #
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

        self.do_status_change(_('Ready. Waiting for action…'))

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
        self.btn_file_new.set_tooltip_markup(
            _('Create an empty BIB database')
        )
        self.btn_file_new.connect('clicked', self.on_file_new_clicked)
        icon = Gio.ThemedIcon(name='document-new-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_file_new.add(image)
        self.btn_file_new.set_relief(Gtk.ReliefStyle.NONE)

        bbox_file.add(self.btn_file_new)

        self.btn_file_open = Gtk.Button()
        self.btn_file_open.set_tooltip_markup(
            _('Open an existing BIB database')
        )
        self.btn_file_open.connect('clicked', self.on_file_open_clicked)
        icon = Gio.ThemedIcon(name='document-open-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_file_open.add(image)
        self.btn_file_open.set_relief(Gtk.ReliefStyle.NONE)

        bbox_file.add(self.btn_file_open)

        hb.pack_start(bbox_file)

        # object-select-symbolic
        self.btn_file_select = Gtk.Button()
        self.btn_file_select.set_tooltip_markup(
            _('Select databases to display in main view')
        )
        self.btn_file_select.add(flat_unclickable_button_in_hbox(
            'file_select', _('Library'),
            icon_name='drive-multidisk-symbolic',
        ))

        self.files_popover = BibedDatabasePopover(
            self.btn_file_select, window=self)

        self.btn_file_select.connect('clicked',
                                     self.on_file_select_clicked,
                                     self.files_popover)

        # bbox_file.add(self.btn_file_select)
        hb.pack_start(self.btn_file_select)

        # —————————————————————————————————— Buttons that act on one entry only

        bbox_entry_one = widget_properties(
            Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL),
            classes=['linked'],
        )

        self.btn_add = Gtk.Button()
        self.btn_add.set_tooltip_markup(
            _('Add a bibliography entry')
        )
        icon = Gio.ThemedIcon(name='list-add-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_add.add(image)
        self.btn_add.connect('clicked', self.on_entry_add_clicked)

        bbox_entry_one.add(self.btn_add)

        self.btn_dupe = Gtk.Button()
        self.btn_dupe.set_tooltip_markup(
            _('Duplicate a bibliography entry into a new one')
        )
        icon = Gio.ThemedIcon(name='edit-copy-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_dupe.add(image)
        self.btn_dupe.connect('clicked', self.on_entry_duplicate_clicked)

        bbox_entry_one.add(self.btn_dupe)

        hb.pack_start(bbox_entry_one)

        # ————————————————————————————— Buttons that act on one or MORE entries

        bbox_entry_multi = widget_properties(
            Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL),
            classes=['linked'],
        )

        self.btn_move = Gtk.Button()
        self.btn_move.set_tooltip_markup(
            _('Move selected entries to another database')
        )
        icon = Gio.ThemedIcon(name='go-next-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_move.add(image)
        self.btn_move.connect('clicked', self.on_entries_move_clicked)

        bbox_entry_multi.add(self.btn_move)

        self.btn_delete = Gtk.Button()  # edit-delete-symbolic
        self.btn_delete.set_tooltip_markup(
            _('Trash or delete selected entries')
        )
        icon = Gio.ThemedIcon(name='list-remove-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_delete.add(image)
        self.btn_delete.connect('clicked', self.on_entries_delete_clicked)

        bbox_entry_multi.add(self.btn_delete)

        hb.pack_start(bbox_entry_multi)

        # ————————————————————————————— Right side, from end to start

        self.btn_preferences = Gtk.Button()
        self.btn_preferences.set_tooltip_markup(
            _('Show application preferences')
        )
        icon = Gio.ThemedIcon(name='preferences-system-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_preferences.add(image)
        self.btn_preferences.connect(
            'clicked', self.on_preferences_clicked)

        hb.pack_end(self.btn_preferences)

        hb.pack_end(self.stack_switcher)

        self.btn_search = Gtk.Button()
        self.btn_search.set_tooltip_markup(
            _('Start searching in selected databases')
        )
        icon = Gio.ThemedIcon(name='system-search-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_search.add(image)
        self.btn_search.connect('clicked', self.on_search_clicked)

        hb.pack_end(self.btn_search)

        self.headerbar = hb

    def setup_booked(self):

        self.lbl_booked = widget_properties(
            label_with_markup(
                _('<big>Something will be here</big>\n\n'
                  'Upcoming feature. Please wait.\n'
                  '(You have no choice, anyway :-D)\n'
                  '<a href="{discuss_en}">Come discuss it on Telegram</a> '
                  'if you wish.').format(
                    discuss_en=BIBED_ASSISTANCE_EN,
                    discuss_fr=BIBED_ASSISTANCE_FR,
                ),
                name='network',
                xalign=0.5,
                yalign=0.5,
            ),
            expand=True,
            selectable=False,
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

        # setup a treeview replacer when no file is loaded.

        self.treeview_placeholder = widget_properties(
            label_with_markup(
                _('<big>Welcome to Bibed!</big>\n\n'
                  'You have no open bibliography yet.\n'
                  'You can create a new one, or load an exising one,\n'
                  'via icon-tools in the upper left corner.\n\n'
                  'In case you need human help,\n'
                  'you can <a href="{discuss_en}">'
                  'reach us on Telegram</a>.\n\n'
                  'Best regards,\n'
                  'Olivier, Corinne\n'
                  'and all Bibed contributors').format(
                    discuss_en=BIBED_ASSISTANCE_EN,
                    discuss_fr=BIBED_ASSISTANCE_FR,
                ),
                name='treeview_placeholder',
                xalign=0.5,
                yalign=0.5,
            ),
            expand=True,
            selectable=False,
        )

    # ————————————————————————————————————————————————— Window & buttons states

    def update_title(self):

        # assert lprint_caller_name(levels=5)
        # assert lprint_function_name()

        # This will automatically count or exclude user or system files,
        # because this points either to the TreeModelFilter or the main model.
        row_count = len(self.treeview.get_model())

        active_databases = self.get_selected_databases()
        active_databases_count = len(active_databases)

        if active_databases_count == self.application.files.num_user:
            # All user files are selected.

            search_text = self.get_search_text()

            if search_text:
                # We have to gather files count from
                # current global filter results.

                files_count = len(self.matched_databases)

            else:
                files_count = self.application.files.num_user

        else:
            files_count = active_databases_count

        if active_databases:
            title_value = '{app} – {text}'.format(
                app=APP_NAME,
                text=(active_databases[0].friendly_filename)
                if active_databases_count == 1
                else n_(
                    '{count} file selected',
                    '{count} files selected',
                    active_databases_count
                ).format(count=active_databases_count)
            )

            subtitle_value = _('{items} in {files}').format(
                items=n_(
                    '{count} item',
                    '{count} items',
                    row_count,
                ).format(count=row_count),
                files=n_(
                    '{count} file',
                    '{count} files',
                    files_count,
                ).format(count=files_count)
            )

        else:
            if self.application.files.num_user:
                title_value = _('{app} – no file selected').format(app=APP_NAME)
                subtitle_value = _('select at least one file to display in your library')
            else:
                title_value = _('{0} – Welcome!').format(APP_NAME)
                subtitle_value = None

        self.headerbar.props.title = title_value
        self.headerbar.props.subtitle = subtitle_value

        LOGGER.debug('update_title(): {0} and {1}.'.format(
                     title_value, subtitle_value))

    def sync_buttons_states(self, sync_children=True, *args, **kwargs):
        ''' Hide or disable relevant widgets, determined by context.

            This method is called either “as-is” (without argument) by
            application, or with arguments by connected signalsself.
            In both cases we don't use arguments, and re-determine the
            context from scratch.

        '''

        # assert lprint_caller_name(levels=5)

        bibed_widgets_base = (
            self.btn_file_new,
            self.btn_file_open,
        )
        bibed_widgets_conditional = (
            self.btn_search,

            # file-related buttons
            self.btn_file_select,
            # TODO: insert popover buttons here,
            #       or forward state to popover.

            # Entry-related buttons.
            self.btn_add, self.btn_dupe, self.btn_move, self.btn_delete,
        )

        if self.stack.is_child_visible('bibed'):

            widgets_show(bibed_widgets_base)

            how_many_files = self.application.files.num_user

            if how_many_files:
                widget_replace(self.treeview_placeholder, self.treeview)
                self.treeview.show()

                widgets_show(bibed_widgets_conditional)

            else:
                widgets_hide(bibed_widgets_conditional)
                widget_replace(self.treeview, self.treeview_placeholder)
                self.treeview_placeholder.show()

            if sync_children:
                self.files_popover.sync_buttons_states(sync_parent=False)

        else:
            widgets_hide(bibed_widgets_base + bibed_widgets_conditional)

    def entry_selection_buttons_set_sensitive(self):

        btns_none_on = tuple()
        btns_none_off = (self.btn_dupe, self.btn_move, self.btn_delete, )

        btns_one_on = (self.btn_dupe, self.btn_move, self.btn_delete, )
        btns_one_off = tuple()

        btns_multi_on = (self.btn_move, self.btn_delete, )
        btns_multi_off = (self.btn_dupe, )

        def set_sensitive(btns_on, btns_off):

            for button in btns_on:
                button.set_sensitive(True)

            for button in btns_off:
                button.set_sensitive(False)

        try:
            selected_count = len(self.treeview.get_selected_rows())

        except TypeError:
            selected_count = 0

        if selected_count > 1:
            set_sensitive(btns_multi_on, btns_multi_off)

        elif selected_count == 1:
            set_sensitive(btns_one_on, btns_one_off)

        else:
            set_sensitive(btns_none_on, btns_none_off)

    # ———————————————————————————————————————————————————————————— “ON” actions

    def on_treeview_selection_changed(self, *args, **kwargs):

        self.entry_selection_buttons_set_sensitive()

    @only_one_when_idle
    def on_window_state_changed(self, window, event):

        state = event.new_window_state

        if state & Gdk.WindowState.WITHDRAWN:
            return

        is_maximized = int(state & Gdk.WindowState.MAXIMIZED)

        self.action_maximize.set_state(GLib.Variant.new_boolean(is_maximized))

        memories.main_window_is_maximized = is_maximized

    def on_maximize_toggle(self, action, value):

        action.set_state(GLib.Variant.new_boolean(value))

        is_maximized = value

        if is_maximized:
            self.maximize()
        else:
            self.unmaximize()

    @run_at_most_every(1000)
    def on_resize(self, window):

        previous_width, previous_height = self.current_size
        current_width, current_height = self.get_size()

        if previous_width == current_width:
            # Avoid useless loops (on Alt-tab there are a lot).
            return

        # Keep in memory for next resize.
        self.current_size = (current_width, current_height)

        # Do not save dimensions if maximized.
        # This allows, at next sessions, to restore a smaller size
        # When unmaximizing, if the app has started maximized.
        if gpod('remember_windows_states') and not self.props.is_maximized:
            memories.main_window_dimensions = self.current_size

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
            return Gdk.EVENT_STOP

        # get search context
        search_text = self.search.get_text().strip()

        keyval = event.keyval

        # TODO: convert all of these to proper accels.
        #       See  http://gtk.10911.n7.nabble.com/GdkModifiers-bitmask-and-GDK-SHIFT-MASK-question-td4404.html
        #       And https://stackoverflow.com/a/10890393/654755
        #       Control+Shift-u → Control+U
        #

        # check the event modifiers (can also use SHIFTMASK, etc)
        ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)
        # only shift = (event.state & Gdk.ModifierType.SHIFT_MASK)
        ctrl_shift = (
            event.state & (Gdk.ModifierType.CONTROL_MASK
                           | Gdk.ModifierType.SHIFT_MASK)
        )

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

        elif ctrl_shift and keyval == Gdk.KEY_F:
            # NOTE: the upper case 'F'

            self.treeview.copy_entries_files_to_clipboard()

        elif ctrl_shift and keyval == Gdk.KEY_T:

            self.treeview.switch_tooltips()

        elif ctrl and keyval == Gdk.KEY_s:

            if not gpod('bib_auto_save'):
                LOGGER.info('Control-S pressed (no action yet).')

            # TODO: save selected files.

        elif ctrl and keyval == Gdk.KEY_r:

            # keep memory, in case file order change during reload.
            selected_databases = tuple(self.application.files.selected_databases)

            with self.block_signals():
                # Don't let combo change and update “memories” while we
                # just reload files to attain same conditions as now.
                self.application.reload_databases(
                    _('Reloaded all open databases at user request.')
                )

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

        elif ctrl and keyval == Gdk.KEY_d:
            if len(self.treeview.get_selected_rows()) == 1:
                self.btn_dupe.emit('clicked')

        elif not ctrl and keyval == Gdk.KEY_Delete:
            self.btn_delete.emit('clicked')

        elif ctrl and keyval == Gdk.KEY_o:
            self.btn_file_open.emit('clicked')

        elif ctrl and keyval == Gdk.KEY_w:

            for database in tuple(
                    self.application.files.selected_user_databases):
                self.application.close_database(database)

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
            return Gdk.EVENT_PROPAGATE

        # Stop propagation of signal, we handled it.
        return Gdk.EVENT_STOP

    # ——————————————————————————————————————————————————————————— Files buttons

    def on_file_new_clicked(self, button):
        ''' Create a new file. '''

        dialog = Gtk.FileChooserDialog(
            _('Please create a new BIB file'), self,
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        dialog.set_current_name(_('Untitled bibliography.bib'))
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
            _('Please choose one or more BIB file'), self,
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
                        self.application.open_file(filename)
                    )

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

    def autoselect_destination(self):

        get_database = self.application.files.get_database
        user_databases = tuple(self.application.files.user_databases)
        selected_user_databases = tuple(
            self.application.files.selected_user_databases)

        # We start with that.
        selected_database = None

        # This will eventually help.
        last_selected_filename = (
            memories.last_destination
            if gpod('remember_last_destination')
            else None
        )

        if len(user_databases) == 1:
            if not selected_user_databases:
                # Only one file, select i before creation
                # for new entry to appear in it when saved.
                self.set_selected_databases(user_databases)

            selected_database = user_databases[0]

        else:
            # There are more than one databases loaded.
            # Else we could not have gotten here, because
            # add_entry button is not visible and keyboard
            # shortcut is inactive.
            if len(selected_user_databases) == 1:
                selected_database = selected_user_databases[0]

            elif len(selected_user_databases) > 1:
                if last_selected_filename:
                    try:
                        last_database = get_database(
                            filename=last_selected_filename)

                    except NoDatabaseForFilenameError:
                        # Life has changed since last destination
                        # was remembered. Forget it.
                        del memories.last_destination

                    else:
                        if last_database in selected_user_databases:
                            selected_database = last_database

        return selected_database

    def on_entry_add_clicked(self, button):

        entry_add_dialog = BibedEntryTypeDialog(parent=self)
        response = entry_add_dialog.run()

        if response == Gtk.ResponseType.OK:
            entry_type = entry_add_dialog.get_entry_type()

            entry_add_dialog.hide()

            entry = BibedEntry.new_from_type(entry_type)

            entry.database = self.autoselect_destination()

            return self.entry_edit(
                entry, message_base=_('{entry} added to {database}.'))

    def on_entry_duplicate_clicked(self, button):

        # Actions can be triggered only if one entry selected.
        selected_entry = self.treeview.get_selected_entries()[0]

        dupe_entry = BibedEntry.new_from_entry(selected_entry)

        return self.entry_edit(
            dupe_entry, message_base=_('{entry} added to {database}.'))

    def on_entries_move_clicked(self, button):

        selected_entries = self.treeview.get_selected_entries()

        if selected_entries is None:
            return

        destination, moved_count, unchanged_count = BibedMoveDialog(
            self, selected_entries, self.application.files).run()

        if destination and moved_count > 0:
            self.do_status_change(
                n_(
                    '{count} entry moved to {destination}{unchanged}.',
                    '{count} entries moved to {destination}{unchanged}.',
                    moved_count,
                ).format(
                    count=moved_count,
                    destination=destination,
                    unchanged=_(', and {count} already there').format(unchanged_count)
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

            selected_count = len(selected_entries)

            self.do_status_change(
                n_(
                    '{count} entry {what}.',
                    '{count} entries {what}.',
                    selected_count,
                ).format(
                    count=selected_count,
                    what=_('trashed')
                    if use_trash
                    else _('definitively deleted')
                )
            )

        if trashed_entries:
            self.ask_and_delete_entries(trashed_entries, trashed=True)

            trashed_count = len(trashed_entries)

            self.do_status_change(
                n_(
                    '{count} previously trashed entry '
                    'definitively deleted.',
                    '{count} previously trashed entries '
                    'definitively deleted.',
                    trashed_count,
                ).format(
                    count=trashed_count)
            )

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

        if trashed:
            title = n_(
                'Wipe {count} entry from trash?',
                'Wipe {count} entries from trash?',
                entries_count,
            ).format(
                count=entries_count)
        else:
            title = n_(
                'Delete {count} entry?',
                'Delete {count} entries?',
                entries_count,
            ).format(count=entries_count)

        entry = selected_entries[0]
        entries_list = markup_entries(selected_entries, entries_count)

        database_count = len(set([
            entry.database for entry in selected_entries
        ]))

        secondary_text = (
            n_(
                'This will permanently delete {entry} from your database.',
                'This will permanently delete the following entries:\n'
                '{entries_list}\n from {from_files}.',
                entries_count,
            ).format(
                entry=entry,
                entries_list=entries_list,
                from_files=n_(
                    '{count} database',
                    '{count} databases',
                    database_count,
                ).format(count=database_count)
            )
        )

        secondary_text += _('\n\nThis action cannot be undone. Are you sure?')

        message_dialog(
            self, Gtk.MessageType.WARNING,
            title, secondary_text,
            delete_callback, selected_entries
        )

    def entry_edit(self, entry, message_base=None):

        entry_edit_dialog = BibedEntryDialog(parent=self, entry=entry)

        response = entry_edit_dialog.run()

        if response:
            # Update the number of entries if relevant.
            self.update_title()

            if message_base is None:
                message_base = _('{entry} modified in {database}.')

            message = message_base.format(
                entry=response, database=database.friendly_filename)

            self.do_status_change(message)

        entry_edit_dialog.destroy()

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
        filter_bib.set_name(_('Bib(La)Tex files'))
        filter_bib.add_pattern('*.bib')

        return filter_bib

    def get_selected_databases(self, with_type=False, only_ids=False):

        selected_databases = tuple(self.application.files.selected_databases)

        if with_type:
            return [
                (database.filename, database.filetype, )
                for database in selected_databases
            ]

        if only_ids:
            return [
                database.objectid
                for database in selected_databases
            ]

        return selected_databases

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
            self.matched_databases = set()
            self.treeview.set_model(self.application.sorter)
            self.application.filter.refilter()

        if (':' in search_text and len(search_text) > 3) \
                or (':' not in search_text and len(search_text) > 1):
            refilter()

        else:
            refilter()

        self.update_title()

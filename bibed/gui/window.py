
import logging

from bibed.foundations import (
    lprint, ldebug,
    lprint_function_name,
    lprint_caller_name,
)

from bibed.constants import (
    APP_NAME,
    BibAttrs,
    FSCols,
    FileTypes,
    # BIBED_ICONS_DIR,
    SEARCH_WIDTH_NORMAL,
    SEARCH_WIDTH_EXPANDED,
    FILES_COMBO_DEFAULT_WIDTH,
    RESIZE_SIZE_MULTIPLIER,
    BIBED_ASSISTANCE_FR,
    BIBED_ASSISTANCE_EN,
)

from bibed.preferences import memories, gpod
from bibed.utils import get_user_home_directory
from bibed.entry import BibedEntry

from bibed.gui.helpers import (
    # scrolled_textview,
    add_classes,
    remove_classes,
    widget_properties,
    label_with_markup,
)
from bibed.gui.preferences import BibedPreferencesDialog
from bibed.gui.treeview import BibedMainTreeView
from bibed.gui.entry_type import BibedEntryTypeDialog
from bibed.gui.entry import BibedEntryDialog
from bibed.gui.gtk import Gio, GLib, Gtk, Gdk, Pango


LOGGER = logging.getLogger(__name__)


class BibebWindowBlockSignalsContextManager:
    def __init__(self, window):
        self.win = window

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.win.unblock_signals()


class BibEdWindow(Gtk.ApplicationWindow):

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

        self.setup_stack()

        self.setup_headerbar()
        self.setup_statusbar()

        self.setup_vbox()

        self.vbox.pack_start(self.stack, True, True, 0)
        self.vbox.pack_end(self.statusbar, False, True, 0)

        self.add(self.vbox)

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
            'BIB Database'
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
        self.connect("delete-event", self.application.on_quit)

        # ———————————————————————— Left side, from start to end

        bbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        Gtk.StyleContext.add_class(bbox.get_style_context(), "linked")

        self.btn_file_new = Gtk.Button()
        self.btn_file_new.connect("clicked", self.on_file_new_clicked)
        icon = Gio.ThemedIcon(name="document-new-symbolic")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_file_new.add(image)
        bbox.add(self.btn_file_new)

        self.btn_file_open = Gtk.Button()
        self.btn_file_open.connect("clicked", self.on_file_open_clicked)
        icon = Gio.ThemedIcon(name="document-open-symbolic")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_file_open.add(image)
        bbox.add(self.btn_file_open)

        hb.pack_start(bbox)

        self.btn_file_close = Gtk.Button()
        self.btn_file_close.connect("clicked", self.on_file_close_clicked)
        icon = Gio.ThemedIcon(name="window-close-symbolic")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_file_close.add(image)
        self.btn_file_close_switch_icon(False)
        hb.pack_start(self.btn_file_close)

        files_combo = self.setup_files_combobox()
        hb.pack_start(files_combo)

        self.btn_add = Gtk.Button()
        icon = Gio.ThemedIcon(name="list-add-symbolic")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_add.add(image)
        self.btn_add.connect('clicked', self.on_entry_add_clicked)

        hb.pack_start(self.btn_add)

        # ————————————————————————————— Right side, from end to start

        self.btn_preferences = Gtk.Button()
        self.btn_preferences.connect(
            "clicked", self.on_preferences_clicked)

        icon = Gio.ThemedIcon(name="preferences-system-symbolic")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_preferences.add(image)
        hb.pack_end(self.btn_preferences)

        hb.pack_end(self.stack_switcher)

        self.search = Gtk.SearchEntry()
        self.search.connect("search-changed",
                            self.on_search_filter_changed)
        self.search.connect("focus-in-event",
                            self.on_search_focus_event)
        self.search.connect("focus-out-event",
                            self.on_search_focus_event)
        self.search.props.width_chars = SEARCH_WIDTH_NORMAL

        hb.pack_end(self.search)

        self.headerbar = hb

    def files_filter_func(self, model, iter, data):

        # assert lprint_caller_name(levels=5)
        # assert lprint_function_name()
        # assert lprint(model[iter][FSCols.FILENAME],
        #               model[iter][FSCols.FILETYPE],
        #               FileTypes.SYSTEM)

        # Keep only non-system entries in main window ComboBox.
        return model[iter][FSCols.FILETYPE] != FileTypes.SYSTEM

    def setup_files_combobox(self):

        self.filtered_files = self.application.files.filter_new()
        self.filtered_files.set_visible_func(self.files_filter_func)

        files_combo = Gtk.ComboBox.new_with_model(self.filtered_files)
        files_combo.connect('changed', self.on_files_combo_changed)

        renderer_text = Gtk.CellRendererText(
            ellipsize=Pango.EllipsizeMode.START)
        renderer_text.props.max_width_chars = (
            FILES_COMBO_DEFAULT_WIDTH * RESIZE_SIZE_MULTIPLIER
        )

        # TODO: replace this combo with a Gtk.StackSidebar()
        # https://lazka.github.io/pgi-docs/Gtk-3.0/classes/StackSidebar.html

        files_combo.pack_start(renderer_text, True)
        files_combo.add_attribute(renderer_text, 'text', 0)
        files_combo.set_sensitive(False)

        self.cmb_files_renderer = renderer_text
        self.cmb_files = files_combo
        self.cmb_files.set_size_request(150, -1)

        return self.cmb_files

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

        self.treeview = BibedMainTreeView(
            model=self.application.data,
            application=self.application,
            clipboard=self.application.clipboard,
            window=self,
        )

        self.treeview_sw.add(self.treeview)

    def update_title(self):

        # assert lprint_caller_name(levels=5)
        # assert lprint_function_name()

        row_count = len(self.treeview.get_model())

        try:
            active_file = self.get_selected_filename()

        except TypeError:
            # Application is closing, we have no file left open.
            active_file = None

        # TODO: translate “All”
        if active_file == 'All':

            search_text = self.get_search_text()

            if search_text:
                # We have to gather files count from current results.

                files_matched = set()

                for row in self.treeview.get_model():
                    files_matched.add(row[BibAttrs.FILENAME])

                # assert lprint(files_matched)

                file_count = len(files_matched)

            else:
                file_count = len(self.cmb_files.get_model())

                if file_count > 2:
                    # Remove the “All” entry
                    file_count -= 1

        elif active_file is None:
            file_count = 0

        else:
            file_count = 1

        title_value = '{0}'.format(APP_NAME)

        subtitle_value = '{0} item{1} in {2} file{3}'.format(
            row_count,
            's' if row_count > 1 else '',
            file_count,
            's' if file_count > 1 else '',
        )

        self.headerbar.props.title = title_value
        self.headerbar.props.subtitle = subtitle_value

        assert ldebug('update_title() to {0} and {1}.'.format(
                      title_value, subtitle_value))

    def sync_shown_hidden(self):
        ''' Hide or disable relevant widgets, determined by context. '''

        how_many_files = len(self.filtered_files)

        if how_many_files:
            self.btn_add.show()
            self.btn_file_close.show()
            self.cmb_files.show()

            self.btn_file_close_switch_icon(
                how_many_files > 1 and self.cmb_files.get_active() == 0)

        else:
            self.btn_add.hide()
            self.btn_file_close.hide()
            self.cmb_files.hide()

    # ———————————————————————————————————————————————————————————— “ON” actions

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

        self.cmb_files_renderer.props.max_width_chars = (
            FILES_COMBO_DEFAULT_WIDTH * RESIZE_SIZE_MULTIPLIER
        )
        self.cmb_files.set_size_request(150, -1)
        self.cmb_files.queue_resize()

        self.treeview.set_columns_widths(current_width)

    def on_search_filter_changed(self, entry):
        ''' Signal: chain the global filter method. '''

        self.do_filter_data_store()

    def on_files_combo_changed(self, combo):
        ''' Signal: chain the global filter method. '''

        # assert lprint_caller_name(levels=5)
        # assert lprint_function_name()

        self.do_filter_data_store()

        # TODO: remove call if not needed anymore.
        self.sync_shown_hidden()

    def on_key_pressed(self, widget, event):

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
            self.treeview.copy_single_key_to_clipboard()

        if ctrl and keyval == Gdk.KEY_k:
            self.treeview.copy_raw_key_to_clipboard()

        elif ctrl and keyval == Gdk.KEY_u:

            if gpod('url_action_opens_browser'):
                self.treeview.open_url_in_webbrowser()
            else:
                self.treeview.copy_url_to_clipboard()

        elif ctrl_shift and keyval == Gdk.KEY_U:
            # NOTE: the upper case 'U'

            if gpod('url_action_opens_browser'):
                self.treeview.copy_url_to_clipboard()
            else:
                self.treeview.open_url_in_webbrowser()

        elif ctrl and keyval == Gdk.KEY_s:

            if gpod('bib_auto_save'):
                # propagate signal, we do not need to save.
                return True

            LOGGER.info('Control-S pressed (no action yet).')

            # given cmb_files, save one or ALL files.

        elif ctrl and keyval == Gdk.KEY_r:

            # keep memory, in case file order change during reload.
            combo_selected = self.get_selected_filename()

            with self.block_signals():
                # Don't let combo change and update “memories” while we
                # just reload files to attain same conditions as now.
                self.application.reload_files(
                    'Reloaded all open files at user request.')

            # restore memory / session
            self.set_selected_filename(combo_selected)

            self.do_activate()

        elif ctrl and keyval == Gdk.KEY_f:
            self.search.grab_focus()

        elif ctrl and keyval == Gdk.KEY_comma:
            self.btn_preferences.emit('clicked')

        elif ctrl and keyval == Gdk.KEY_l:
            self.cmb_files.grab_focus()

        elif ctrl and keyval == Gdk.KEY_n:
            self.btn_add.emit('clicked')

        elif ctrl and keyval == Gdk.KEY_o:
            self.btn_file_open.emit('clicked')

        elif ctrl and keyval == Gdk.KEY_w:
            self.btn_file_close.emit('clicked')

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

            # if self.search.has_focus():

            if search_text:
                self.search.set_text('')

                try:
                    del memories.search_text

                except Exception:
                    pass

            else:
                entry = self.treeview.get_selected_store_entry()

                if entry is not None:
                    self.treeview.unselect_all()

                else:
                    if len(self.application.files):
                        if self.cmb_files.get_active() != 0:
                            self.cmb_files.set_active(0)

            self.treeview.grab_focus()

        else:
            # The keycode combination was not handled, propagate.
            return False

        # Stop propagation of signal, we handled it.
        return True

    def on_search_focus_event(self, search, event):

        if self.search.has_focus():
            self.search.props.width_chars = SEARCH_WIDTH_EXPANDED

        else:
            self.search.props.width_chars = SEARCH_WIDTH_NORMAL

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

            # Same problem as in app.do_activate(): when loading more than two
            # files, only the two first fire a on_*changed() signal. Thus we
            # block everything, and compute things manually after load.
            with self.block_signals():
                for filename in filenames:
                    self.application.open_file(filename, recompute=False)

            self.treeview.main_model.do_recompute_global_ids()
            self.do_activate()

        elif response == Gtk.ResponseType.CANCEL:
            pass

        dialog.destroy()

    def on_file_close_clicked(self, button):
        ''' Close current selected file. '''

        how_many_files = len(self.application.files)

        # assert lprint(how_many_files)

        if how_many_files > 1 and self.cmb_files.get_active() == 0:

            store = self.application.files

            # Copy them to let the store update itself
            # smoothly without missing items during loop.
            filenames = store.get_open_filenames()

            # assert lprint(filenames)

            for filename in filenames:
                self.application.close_file(filename, recompute=False)

            # Useless, we closed everything.
            # self.treeview.do_recompute_global_ids()

        else:
            self.application.close_file(self.get_selected_filename())

        self.sync_shown_hidden()

    def on_entry_add_clicked(self, button):

        entry_add_dialog = BibedEntryTypeDialog(parent=self)
        response = entry_add_dialog.run()

        if response == Gtk.ResponseType.OK:
            entry_type = entry_add_dialog.get_entry_type()

            entry_add_dialog.hide()

            entry = BibedEntry.new_from_type(entry_type)

            entry_edit_dialog = BibedEntryDialog(
                parent=self, entry=entry)

            entry_edit_dialog.run()

            # TODO: convert this test to Gtk.Response.OK and CANCEL
            #       to know if we need to insert/update or not.
            if entry.database is not None and entry_edit_dialog.can_save:
                # TODO: insert in self.application.data_store directly ?
                #       abstraction-level question only.
                self.treeview.main_model.insert_entry(entry)
                self.do_filter_data_store()

            entry_edit_dialog.destroy()

        entry_add_dialog.destroy()

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

    # ——————————————————————————————————————————————————————————————————— Other

    def get_bib_filter(self):

        filter_bib = Gtk.FileFilter()
        filter_bib.set_name('Bib(La)Tex files')
        filter_bib.add_pattern('*.bib')

        return filter_bib

    def get_selected_filename(self):

        filename = self.filtered_files[
            self.cmb_files.get_active_iter()
        ][FSCols.FILENAME]

        return filename

    def set_selected_filename(self, filename):

        for row in self.filtered_files:
            if row[FSCols.FILENAME] == filename:
                self.cmb_files.set_active_iter(row.iter)
                break

    def get_search_text(self):

        return self.search.get_text().strip()

    def block_signals(self):
        ''' This function can be used as context manager or not. '''

        self.cmb_files.handler_block_by_func(self.on_files_combo_changed)

        return BibebWindowBlockSignalsContextManager(self)

    def unblock_signals(self):
        self.cmb_files.handler_unblock_by_func(self.on_files_combo_changed)

    # —————————————————————————————————————————————————————————————— DO actions

    def do_activate(self):

        self.update_title()
        self.sync_shown_hidden()
        self.treeview.do_column_sort()

    def do_status_change(self, message):
        self.statusbar.push(
            self.context_id, message)

    def do_filter_data_store(self):
        ''' Filter the data store on filename, search_text, or both. '''

        # assert lprint_caller_name(levels=2)
        # assert lprint_function_name()

        try:
            filename = self.get_selected_filename()

        except TypeError:
            filename = None

        if filename is not None:
            if memories.combo_filename != filename:
                memories.combo_filename = filename
        else:
            if memories.combo_filename is not None:
                del memories.combo_filename

        search_text = self.get_search_text()

        if search_text:
            if memories.search_text != search_text:
                memories.search_text = search_text
        else:
            if memories.search_text is not None:
                del memories.search_text

        def refilter():
            self.treeview.set_model(self.application.sorter)
            self.application.filter.refilter()

        if (':' in search_text and len(search_text) > 3) \
                or (':' not in search_text and len(search_text) > 1):
            refilter()

        else:
            # TODO: translate 'All'
            if filename is None or filename == 'All':
                # No search, no filename; get ALL data, unfiltered.
                self.treeview.set_model(self.application.data)

            else:
                refilter()

        self.update_title()

    def btn_file_close_switch_icon(self, multiple=False):

        if multiple:
            # self.btn_file_close.set_relief(Gtk.ReliefStyle.NORMAL)
            add_classes(self.btn_file_close, ['close-all'])
            self.btn_file_close.set_tooltip_markup(
                'Close <b>ALL</b> open files')
        else:
            # self.btn_file_close.set_relief(Gtk.ReliefStyle.NONE)
            remove_classes(self.btn_file_close, ['close-all'])
            self.btn_file_close.set_tooltip_markup(
                'Close <i>currently selected</i> file')

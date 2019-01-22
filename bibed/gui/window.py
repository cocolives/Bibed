
import os
import logging

# from bibed.foundations import ltrace_function_name

from bibed.constants import (
    APP_NAME,
    BIBED_ICONS_DIR,
    SEARCH_WIDTH_NORMAL,
    SEARCH_WIDTH_EXPANDED,
    BibAttrs,
)

from bibed.preferences import memories, gpod
from bibed.utils import get_user_home_directory
from bibed.entry import BibedEntry

from bibed.gui.helpers import scrolled_textview
from bibed.gui.preferences import BibedPreferencesDialog
from bibed.gui.entry_type import BibedEntryTypeDialog
from bibed.gui.entry import BibedEntryDialog
from bibed.gui.gtk import Gio, GLib, Gtk, Gdk, Pango


LOGGER = logging.getLogger(__name__)


class BibEdWindow(Gtk.ApplicationWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        self.connect("key-press-event", self.on_key_pressed)

        # self.set_icon_name('accessories-dictionary')
        self.set_icon_from_file(os.path.join(
            BIBED_ICONS_DIR, 'accessories-dictionary.png'))

        # TODO: use gui.helpers.get_screen_resolution()
        dimensions = (1200, 600)

        if gpod('remember_windows_states'):
            remembered_dimensions = memories.main_window_dimensions

            if remembered_dimensions is not None:
                dimensions = remembered_dimensions

        self.set_default_size(*dimensions)

        # keep for resize() operations smothing.
        self.current_size = dimensions

        # self.set_border_width(10)

        # prepared for future references.
        self.preferences_dialog = None

        # ———————————————————————————————————————————————————————— BibEd Window

        self.application = kwargs['application']

        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        self.setup_treeview()
        self.setup_textview()

        self.setup_stack()

        self.setup_headerbar()
        self.setup_statusbar()

        self.setup_vbox()

        self.vbox.pack_start(self.stack, True, True, 0)
        self.vbox.pack_end(self.statusbar, False, True, 0)

        self.add(self.vbox)

    def setup_stack(self):

        stack = Gtk.Stack()

        stack.set_transition_type(
            Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        stack.set_transition_duration(500)

        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(stack)

        stack.add_titled(
            self.treeview_sw,
            "treeview",
            "Database"
        )

        stack.child_set_property(
            self.treeview_sw, "icon-name",
            'accessories-dictionary-symbolic')

        stack.add_titled(
            self.textview_sw,
            "strings",
            "BIB Strings"
        )

        stack.child_set_property(
            self.textview_sw, "icon-name",
            'view-list-symbolic')
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

        files_combo = Gtk.ComboBox.new_with_model(
            self.application.files_store)
        files_combo.connect("changed", self.on_files_combo_changed)

        renderer_text = Gtk.CellRendererText(
            ellipsize=Pango.EllipsizeMode.START)
        renderer_text.props.max_width_chars = 20

        files_combo.pack_start(renderer_text, True)
        files_combo.add_attribute(renderer_text, "text", 0)
        files_combo.set_sensitive(False)
        hb.pack_start(files_combo)

        self.cmb_files_renderer = renderer_text
        self.cmb_files = files_combo

        self.btn_add = Gtk.Button()
        icon = Gio.ThemedIcon(name="list-add-symbolic")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_add.add(image)
        self.btn_add.connect('clicked', self.on_entry_add_clicked)

        hb.pack_start(self.btn_add)

        self.btn_file_close = Gtk.Button()
        self.btn_file_close.connect("clicked", self.on_file_close_clicked)
        icon = Gio.ThemedIcon(name="window-close-symbolic")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        self.btn_file_close.add(image)
        self.btn_file_close_switch_icon(False)
        hb.pack_start(self.btn_file_close)

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

    def setup_textview(self):

        self.textview_sw, self.textview = scrolled_textview()

    def setup_treeview(self):

        self.treeview_sw = Gtk.ScrolledWindow()
        # scrolledwindow.set_hexpand(True)
        # self.treeview_sw.set_vexpand(True)
        self.treeview_sw.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC
        )

        self.treeview = Gtk.TreeView(model=self.application.data_store)

        # We get better search via global SearchEntry
        self.treeview.set_enable_search(False)

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

        self.treeview_sw.add(self.treeview)

        select = self.treeview.get_selection()
        select.connect("changed", self.on_treeview_selection_changed)

        self.treeview.connect('row-activated', self.on_treeview_row_activated)

        select.unselect_all()

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
        self.treeview.append_column(column)

        return column

    def update_title(self):

        row_count = len(self.treeview.get_model())
        file_count = len(self.cmb_files.get_model())

        # TODO: update the file count if search filtered

        if file_count > 1:
            # do not count the 'All' item
            file_count -= 1

        title_value = '{0}'.format(APP_NAME)

        subtitle_value = '{0} item{1} in {2} file{3}'.format(
            row_count,
            's' if row_count > 1 else '',
            file_count,
            's' if file_count > 1 else '',)

        self.headerbar.props.title = title_value
        self.headerbar.props.subtitle = subtitle_value

        if __debug__:
            LOGGER.debug('update_title() to {0} and {1}.'.format(
                title_value, subtitle_value))

    def sync_shown_hidden(self):
        ''' Hide or disable relevant widgets, determined by context. '''

        how_many_files = len(self.application.files_store)

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

        # Remove 1 else the treeview gets a few pixels too wide.
        # The last column will compensate any "missing" pixels,
        # and we get no horizontal scrollbar.
        column_width = round(current_width * 0.125) - 1

        self.col_key.set_min_width(column_width)
        self.col_author.set_min_width(column_width)
        self.col_journal.set_min_width(column_width)

        self.treeview.columns_autosize()

        # TODO: this doesn't seem to work; on resizes()
        #       the ComboBox width doesn't change.
        self.cmb_files_renderer.props.max_width_chars = \
            round(column_width / 20)

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

        store = self.application.data_store
        files = self.application.files

        treeiter = store.get_iter(path)

        # value = store.get_value(treeiter, 1)
        bib_key = store[treeiter][BibAttrs.KEY]
        filename = store[treeiter][BibAttrs.FILENAME]

        entry = files[filename].get_entry_by_key(bib_key)

        assert(isinstance(entry, BibedEntry))

        entry_edit_dialog = BibedEntryDialog(
            parent=self, entry=entry)

        response = entry_edit_dialog.run()

        if response == Gtk.ResponseType.OK:
            pass

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

    def on_search_filter_changed(self, entry):
        ''' Signal: chain the global filter method. '''

        self.do_filter_data_store()

    def on_files_combo_changed(self, combo):
        ''' Signal: chain the global filter method. '''

        self.do_filter_data_store()

        # TODO: remove call if not needed anymore.
        self.sync_shown_hidden()

    def on_key_pressed(self, widget, event):

        # get search context
        search_text = self.search.get_text().strip()

        keyval = event.keyval
        # state = event.state

        # check the event modifiers (can also use SHIFTMASK, etc)
        ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)

        # Alternative way of knowing key pressed.
        # keyval_name = Gdk.keyval_name(keyval)
        # if ctrl and keyval_name == 's':

        if ctrl and keyval == Gdk.KEY_s:
            LOGGER.info('Control-S pressed (no action yet).')

        elif ctrl and keyval == Gdk.KEY_r:
            self.application.reload_file(
                '{} reloaded at user request.'.format(
                    self.application.filename))

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

        elif keyval == Gdk.KEY_Escape:

            # if self.search.has_focus():

            if search_text:
                self.search.set_text('')

                try:
                    del memories.search_text

                except Exception:
                    pass

            else:
                if len(self.application.files_store):
                    if self.cmb_files.get_active() != 0:
                        self.cmb_files.set_active(0)

            self.treeview.grab_focus()

        else:
            return False

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

            for filename in filenames:
                self.application.open_file(filename, recompute=False)

            self.application.do_recompute_global_ids()

        elif response == Gtk.ResponseType.CANCEL:
            pass

        dialog.destroy()

    def on_file_close_clicked(self, button):
        ''' Close current selected file. '''

        how_many_files = len(self.application.files_store)

        if how_many_files > 1 and self.cmb_files.get_active() == 0:

            store = self.application.files_store

            # Copy them to let the store update itself
            # smoothly without missing items during loop.
            filenames = [store[i][0] for i in range(1, len(store))]

            for filename in filenames:
                self.application.close_file(filename, recompute=False)

            # Useless, we closed everything.
            # self.application.do_recompute_global_ids()

        else:
            self.application.close_file(self.get_files_combo_filename())

        self.sync_shown_hidden()

    def on_entry_add_clicked(self, button):

        entry_add_dialog = BibedEntryTypeDialog(parent=self)
        response = entry_add_dialog.run()

        if response == Gtk.ResponseType.OK:
            entry_type = entry_add_dialog.get_entry_type()

            entry_add_dialog.hide()

            entry_edit_dialog = BibedEntryDialog(
                parent=self, entry=BibedEntry.new_from_type(entry_type))

            response = entry_edit_dialog.run()

            if response == Gtk.ResponseType.OK:
                pass

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

    def get_bib_filter(self):

        filter_bib = Gtk.FileFilter()
        filter_bib.set_name('Bib(La)Tex files')
        filter_bib.add_pattern('*.bib')

        return filter_bib

    def get_files_combo_filename(self):

        filename = self.application.files_store[
            self.cmb_files.get_active_iter()
        ][0]

        return filename

    def get_search_text(self):

        return self.search.get_text().strip()

    def do_treeview_column_sort(self):

        if memories.treeview_sort_column is not None:
            # print('setting column')

            for col in self.treeview.get_columns():
                if col.props.title == memories.treeview_sort_column:

                    # print('COL', col.props.title)
                    # print(col.get_sort_order())
                    col.props.sort_order = memories.treeview_sort_order
                    # print(col.get_sort_order())
                    # print(col.get_sort_indicator())
                    col.props.sort_indicator = memories.treeview_sort_indicator
                    # print(col.get_sort_indicator())

    def do_status_change(self, message):
        self.statusbar.push(
            self.context_id, message)

    def do_filter_data_store(self):
        ''' Filter the data store on filename, search_text, or both. '''

        # print(ltrace_function_name())

        try:
            filename = self.get_files_combo_filename()

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
                self.treeview.set_model(self.application.data_store)
                self.col_id.props.visible = False
                self.col_global_id.props.visible = True

            else:
                if self.col_global_id.props.visible:
                    self.col_global_id.props.visible = False
                    self.col_id.props.visible = True

                refilter()

        self.update_title()

    def btn_file_close_switch_icon(self, multiple=False):

        if multiple:
            self.btn_file_close.set_relief(Gtk.ReliefStyle.NORMAL)

        else:
            self.btn_file_close.set_relief(Gtk.ReliefStyle.NONE)

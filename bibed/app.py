
import os
import time
import pyinotify
import logging

from threading import Lock
from collections import OrderedDict

from bibed.constants import (
    APP_ID,
    APP_NAME,
    APP_VERSION,
    APP_MENU_XML,
    BIBED_DATA_DIR,
    STORE_LIST_ARGS,
    BibAttrs,
)

from bibed.foundations import (
    # ltrace_function_name,
    touch_file,
    NoWatchContextManager,
)

# Import Gtk before preferences, to initialize GI.
from bibed.gui.gtk import Gio, GLib, Gtk, Gdk, Notify

from bibed.utils import PyinotifyEventHandler
from bibed.preferences import preferences, memories
from bibed.database import BibedDatabase

from bibed.gui.window import BibEdWindow


LOGGER = logging.getLogger(__name__)


class BibEdApplication(Gtk.Application):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                         **kwargs)

        self.add_main_option(
            "test", ord("t"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Command line test", None)

        self.window = None
        self.files = OrderedDict()
        self.bibdb = None

    def do_startup(self):
        Gtk.Application.do_startup(self)

        self.setup_css()
        self.setup_actions()
        self.setup_app_menu()
        self.setup_data_stores()
        self.setup_inotify()

        self.file_modify_lock = Lock()

    def setup_css(self):

        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_path(
            os.path.join(BIBED_DATA_DIR, 'style.css'))

        self.style_context = Gtk.StyleContext()
        self.style_context.add_provider_for_screen(
            Gdk.Screen.get_default(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def setup_actions(self):

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)

    def setup_app_menu(self):

        builder = Gtk.Builder.new_from_string(APP_MENU_XML, -1)
        self.set_app_menu(builder.get_object("app-menu"))

    def setup_data_stores(self):

        # Stores filenames. Linked to self.files.keys()
        self.files_store = Gtk.ListStore(
            str,
        )

        # Stores BIB entries. Linked to self.files.values()
        self.data_store = Gtk.ListStore(
            *STORE_LIST_ARGS
        )

        # Keep the filter data sortable along the way.

        self.filter = self.data_store.filter_new()
        self.sorter = Gtk.TreeModelSort(self.filter)
        self.filter.set_visible_func(self.filter_method)

        self.preamble = Gtk.TextBuffer()

    def setup_inotify(self):

        PyinotifyEventHandler.app = self

        self.wm = pyinotify.WatchManager()
        self.notifier = pyinotify.ThreadedNotifier(
            self.wm, PyinotifyEventHandler())
        self.notifier.start()

        self.wdd = {}

    def no_watch(self, filename):

        return NoWatchContextManager(self, filename)

    def inotify_add_watch(self, filename):

        file_to_watch = os.path.realpath(os.path.abspath(filename))

        self.wdd.update(self.wm.add_watch(file_to_watch, pyinotify.IN_MODIFY))

        LOGGER.info('inotify_add_watch(): watching {}.'.format(file_to_watch))

    def inotify_remove_watch(self, filename):

        file_to_watch = os.path.realpath(os.path.abspath(filename))

        self.wm.rm_watch(self.wdd[file_to_watch])

        LOGGER.info(
            'inotify_remove_watch(): removing {}.'.format(
                file_to_watch))

    def filter_method(self, model, iter, data):

        try:
            filter_text = self.window.search.get_text()

        except AttributeError:
            # The window is not yet constructed
            return True

        try:
            filter_file = self.window.get_files_combo_filename()

        except TypeError:
            # The window is not yet constructed.
            return True

        else:
            # TODO: translate 'All'
            if filter_file != 'All':
                if model[iter][BibAttrs.FILENAME] != filter_file:
                    # The current row is not part of displayed
                    # filename. No need to go further.
                    return False

        if filter_text is None:
            return True

        filter_text = filter_text.strip().lower()

        if not filter_text:
            return True

        words = filter_text.split()

        specials = []
        full_text = []

        for word in words:
            if ':' in word:
                specials.append([x.lower() for x in word.split(':')])
            else:
                full_text.append(word)

        for key, val in specials:
            if key == 't':  # TYPE
                if val not in model[iter][BibAttrs.TYPE].lower():
                    return False

            if key == 'k':  # (bib) KEY
                if val not in model[iter][BibAttrs.KEY].lower():
                    return False

            if key == 'j':
                if val not in model[iter][BibAttrs.JOURNAL].lower():
                    return False

            if key == 'y':
                if int(val) != int(model[iter][BibAttrs.YEAR]):
                    return False

        for word in full_text:
            if word not in model[iter][BibAttrs.AUTHOR].lower() \
                    and word not in model[iter][BibAttrs.TITLE].lower():
                return False

        return True

    def do_recompute_global_ids(self):

        if __debug__:
            LOGGER.debug('do_recompute_global_ids()')

        counter = 1
        global_id = BibAttrs.GLOBAL_ID

        for row in self.data_store:
            row[global_id] = counter
            counter += 1

    def do_notification(self, message):

        notification = Notify.Notification.new('Bibed', message)
        # notification.set_timeout(Notify.EXPIRES_NEVER)
        # notification.add_action('quit', 'Quit', notification_callback)
        notification.show()

    def do_activate(self):

        # For GUI-setup-order related reasons,
        # we need to delay some things.
        search_grab_focus = False
        combo_set_active = None

        # We only allow a single window and raise any existing ones
        if not self.window:
            Notify.init(APP_NAME)

            # Windows are associated with the application
            # when the last one is closed the application shuts down
            self.window = BibEdWindow(
                title="Main Window", application=self)
            self.window.show_all()

            if preferences.remember_open_files:

                if memories.open_files:

                    # 1: search_text needs to be loaded first, else it gets
                    # wiped when file_combo is updated with re-loaded files.
                    # 2: don't load it if there are no open_files.
                    # 3: dont call do_filter_data_store(), it will be called
                    # by on_files_combo_changed() when files are added.
                    if memories.search_text is not None:
                        self.window.search.set_text(memories.search_text)
                        search_grab_focus = True

                    # Idem, same problem.
                    if memories.combo_filename is not None:
                        combo_set_active = memories.combo_filename

                    # Then, load all previously opened files.
                    # Get a copy to avoid the set being changed while we load,
                    # because in some corner cases the live “re-ordering”
                    # makes a file loaded two times.
                    for filename in memories.open_files.copy():
                        try:
                            self.open_file(filename)

                        except (IOError, OSError):
                            memories.remove_open_file(filename)

        # make interface consistent with data.
        self.window.sync_shown_hidden()
        self.window.do_treeview_column_sort()

        if combo_set_active:
            for row in self.files_store:
                if row[0] == combo_set_active:
                    self.window.cmb_files.set_active_iter(row.iter)
                    break

        if search_grab_focus:
            self.window.search.grab_focus()

        # TODO: remove
        # Show preferences immediately to speed up tests / debug.
        # self.window.btn_preferences.emit('clicked')

        self.window.present()

    def create_file(self, filename):
        ''' Create a new BIB file, then open it in the application. '''

        if __debug__:
            LOGGER.debug('create_file({})'.format(filename))

        touch_file(filename)

        self.open_file(filename)

    def open_file(self, filename, recompute=True):
        ''' Add a file to the application. '''

        if __debug__:
            LOGGER.debug('open_file({}, recompute={})'.format(
                filename, recompute))

        # print(ltrace_function_name())

        for row in self.files_store:
            if row[0] == filename:
                self.do_notification('“{}” already loaded.'.format(filename))
                return

        self.inotify_add_watch(filename)

        self.files[filename] = None
        self.files_store.append((filename, ))

        if len(self.files_store) == 2:
            # Add the magic “All” entry.
            self.files_store.prepend(('All', ))

            # Now that we have more than one file,
            # make active and select 'All' by default.
            self.window.cmb_files.set_active(0)
            self.window.cmb_files.set_sensitive(True)

        else:
            self.window.cmb_files.set_active(0)

        self.load_file_contents(filename, recompute=recompute)

        memories.add_open_file(filename)
        memories.add_recent_file(filename)

    def check_has_key(self, key):

        for filename, database in self.files.items():
            if key in database.keys():
                return filename

        return None

    def reload_file_contents(self, filename, message=None):
        '''Empty everything and reload. '''

        # We try to re-lock to avoid conflict if reloading
        # manually while an inotify reload occurs.
        self.file_modify_lock.acquire(blocking=False)

        if self.load_file_contents(filename, clear_first=True) and message:
            self.window.do_status_change(message)

        try:
            self.file_modify_lock.release()

        except Exception as e:
            LOGGER.exception(e)

    def load_file_contents(self, filename, clear_first=False, recompute=True):
        ''' Fill the GtkTreeStore with BIB data. '''

        if __debug__:
            LOGGER.debug(
                'load_file_contents({}, clear_first={}, recompute={})'.format(
                    filename, clear_first, recompute))

        try:
            new_bibdb = BibedDatabase(filename, self)

        except Exception as e:
            LOGGER.exception('Cannot load file {0} ({1})'.format(filename, e))
            return False

        if clear_first:
            if __debug__:
                LOGGER.debug(
                    'load_file_contents({0}): store cleared.'.format(filename))

            # self.window.treeview.set_editable(False)
            self.clear_file_from_store(filename, recompute=False)
            self.files[filename] = None

        self.files[filename] = new_bibdb

        for entry in new_bibdb.values():
            self.data_store.append(
                entry.to_list_store_row()
            )

        if __debug__:
            LOGGER.debug('load_file_contents({}): end.'.format(filename))

        if recompute:
            self.do_recompute_global_ids()

        self.window.update_title()

        return True

    def clear_file_from_store(self, filename=None, recompute=True):
        ''' Clear the data store from one or more file contents. '''

        if __debug__:
            LOGGER.debug('clear_file_from_store({}, recompute={})'.format(
                filename, recompute))

        if filename is None:
            # clear ALL data.
            self.data_store.clear()
            return

        # keep references handy for speed in loops.
        filename_index = BibAttrs.FILENAME
        store = self.data_store

        for row in store:
            if row[filename_index] == filename:
                    store.remove(row.iter)

        if recompute:
            self.do_recompute_global_ids()

    def save_file_to_disk(self, filename):
        pass

    def close_file(self, filename, save_before=True, recompute=True, remember_close=True):
        ''' Close a file and impact changes. '''

        if __debug__:
            LOGGER.debug('close_file({}, save_before={}, recompute={})'.format(
                filename, save_before, recompute))

        self.inotify_remove_watch(filename)

        if save_before:
            self.save_file_to_disk(filename)

        self.clear_file_from_store(filename, recompute=recompute)

        self.files[filename] = None

        for row in self.files_store:
            if row[0] == filename:
                self.files_store.remove(row.iter)
                break

        if len(self.files_store) == 2:
            # len == 2 is (All, last_file); thus, remove 'All'.
            self.files_store.remove(self.files_store[0].iter)

            # Now that we have more than one file,
            # make active and select 'All' by default.
            self.window.cmb_files.set_active(0)
            self.window.cmb_files.set_sensitive(False)

        else:
            self.window.cmb_files.set_active(0)

        if remember_close:
            memories.remove_open_file(filename)

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()

        # convert GVariantDict -> GVariant -> dict
        options = options.end().unpack()

        if 'test' in options:
            LOGGER.info("Test argument received: %s" % options['test'])

        self.activate()
        return 0

    def on_about(self, action, param):
        about_dialog = Gtk.AboutDialog(
            transient_for=self.window, modal=True)

        about_dialog.set_program_name(APP_NAME)
        about_dialog.set_version(APP_VERSION)
        about_dialog.set_authors(["Olivier Cortès", "Collectif Cocoliv.es"])
        about_dialog.set_copyright("(c) Collectif Cocoliv.es")
        about_dialog.set_comments(
            "Logiciel libre d'assistance bibliographique")
        about_dialog.set_website("https://cocoliv.es/library/bibed")

        about_dialog.present()

    def on_quit(self, action, param):

        if preferences.remember_open_files:
            # We need to keep track of this, because unloading
            # the files will empty the combo and we will loose
            # the selected value.
            combo_value = memories.combo_filename

        for row in self.files_store:
            if row[0] == 'All':
                # TODO: translate 'All'
                continue

            self.close_file(
                row[0],  # filename
                save_before=True,
                recompute=False,

                # This will allow automatic reopen on next launch.
                remember_close=False,
            )

        try:
            self.notifier.stop()

        except Exception:
            pass

        if preferences.remember_open_files:
            # Keep that memory back now that all files are unloaded.
            memories.combo_filename = combo_value

        LOGGER.info('Terminating application.')
        self.quit()

    def on_file_modify(self, event):
        ''' Acquire lock and launch delayed updater. '''

        if self.file_modify_lock.acquire(blocking=False) is False:
            return

        if __debug__:
            LOGGER.debug(
                'Programming reload of {0} when idle.'.format(
                    event.pathname))

        GLib.idle_add(self.on_file_modify_callback, event)

    def on_file_modify_callback(self, event):
        ''' Reload file with a dedicated message. '''

        filename = event.pathname

        if __debug__:
            LOGGER.debug('on_file_modify_callback({})'.format(filename))

        time.sleep(1)

        self.reload_file_contents(
            filename,
            '“{}” reloaded because of external change.'.format(
                filename))

        # Remove the callback from IDLE list.
        return False

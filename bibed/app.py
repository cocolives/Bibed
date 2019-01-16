
import os
import time
import pyinotify
import logging

from threading import Lock
from collections import OrderedDict
from pybtex.database import parse_file as pybtex_parse_file

from bibed.constants import (
    APP_ID,
    APP_NAME,
    APP_VERSION,
    APP_MENU_XML,
    STORE_LIST_ARGS,
    BibAttrs,
)

from bibed.entries import bib_entry_to_store_row_list
from bibed.gui import BibEdWindow

import gi
gi.require_version('Gtk', '3.0')
gi.require_version("Notify", "0.7")
from gi.repository import GLib, Gio, Gtk, Notify  # NOQA


LOGGER = logging.getLogger(__name__)


class EventHandler(pyinotify.ProcessEvent):

    app = None

    def process_IN_MODIFY(self, event):

        LOGGER.debug('Modify event start ({}).'.format(event))

        EventHandler.app.on_file_modify(event)

        LOGGER.debug('Modify event end.')

        return True


def notification_callback(notification, action_name):
    notification.close()
    # Gtk.main_quit()


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

        self.setup_actions()
        self.setup_app_menu()
        self.setup_data_stores()
        self.setup_inotify()

        self.file_modify_lock = Lock()

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

        EventHandler.app = self

        self.wm = pyinotify.WatchManager()
        self.notifier = pyinotify.ThreadedNotifier(
            self.wm, EventHandler())
        self.notifier.start()

        self.wdd = {}

    def inotify_add_watch(self, filename):

        file_to_watch = os.path.realpath(os.path.abspath(filename))

        self.wdd.update(self.wm.add_watch(file_to_watch, pyinotify.IN_MODIFY))

        LOGGER.info('inotify_add_watch(): watching {}.'.format(file_to_watch))

    def inotify_remove_watch(self, filename):

        file_to_watch = os.path.realpath(os.path.abspath(filename))

        self.wm.rm_watch(self.wdd[file_to_watch])

        LOGGER.info(
            'inotify_remove_watch(): removing watch for {}.'.format(
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

        # We only allow a single window and raise any existing ones
        if not self.window:
            Notify.init(APP_NAME)

            # Windows are associated with the application
            # when the last one is closed the application shuts down
            self.window = BibEdWindow(
                title="Main Window", application=self)
            self.window.show_all()

            if not self.files:
                # TODO: get recently loaded files
                # from GNOME / prefs / whatever

                try:
                    default_filename = os.path.realpath(
                        os.path.abspath('bibed.bib'))

                except Exception:
                    pass

                else:
                    self.open_file(default_filename)

        # make interface consistent with data.
        self.window.sync_shown_hidden()
        self.window.present()

    def create_file(self, filename):
        ''' Create a new BIB file, then open it in the application. '''

        LOGGER.debug('create_file({})'.format(filename))

        with open(filename, 'w') as f:
            f.write('\n')

        self.open_file(filename)

    def open_file(self, filename, recompute=True):
        ''' Add a file to the application. '''

        LOGGER.debug('open_file({}, recompute={})'.format(filename, recompute))

        self.inotify_add_watch(filename)

        self.files[filename] = None
        self.files_store.append((filename, ))

        if len(self.files_store) == 2:
            # Add the magic “All” entry.
            self.files_store.prepend(('All', ))

            # Now that we have more than one file,
            # make active and select 'All' by default.
            self.window.files_combo.set_active(0)
            self.window.files_combo.set_sensitive(True)

        else:
            self.window.files_combo.set_active(0)

        self.load_file_contents(filename, recompute=recompute)

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

        LOGGER.debug(
            'load_file_contents({}, clear_first={}, recompute={})'.format(
                filename, clear_first, recompute))

        try:
            new_bibdb = pybtex_parse_file(filename)

        except Exception as e:
            LOGGER.exception('Cannot load file {0} ({1})'.format(filename, e))
            return False

        counter = 1

        if clear_first:
            LOGGER.debug(
                'load_file_contents({0}): store cleared.'.format(filename))
            # self.window.treeview.set_editable(False)
            self.clear_file_from_store(filename, recompute=False)
            self.files[filename] = None

        self.files[filename] = new_bibdb

        for key, entry in new_bibdb.entries.items():
            self.data_store.append(
                bib_entry_to_store_row_list(
                    0, filename, counter, entry)
            )
            counter += 1

        # self.preamble.set_text(self.bibdb.preamble)
        LOGGER.debug('load_file_contents({}): end.'.format(filename))

        if recompute:
            self.do_recompute_global_ids()

        self.window.update_title()

        return True

    def clear_file_from_store(self, filename=None, recompute=True):
        ''' Clear the data store from one or more file contents. '''

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

    def close_file(self, filename, save_before=True, recompute=True):
        ''' Close a file and impact changes. '''

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

        if len(self.files_store) == 2:
            # len == 2 is (All, last_file); thus, remove 'All'.
            self.files_store.remove(self.files_store[0].iter)

            # Now that we have more than one file,
            # make active and select 'All' by default.
            self.window.files_combo.set_active(0)
            self.window.files_combo.set_sensitive(False)

        else:
            self.window.files_combo.set_active(0)

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()

        # convert GVariantDict -> GVariant -> dict
        options = options.end().unpack()

        if "test" in options:
            # This is printed on the main instance
            print("Test argument received: %s" % options["test"])

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

        try:
            self.notifier.stop()
        except Exception:
            pass

        self.quit()

    def on_file_modify(self, event):
        ''' Acquire lock and launch delayed updater. '''

        if self.file_modify_lock.acquire(blocking=False) is False:
            return

        LOGGER.debug(
            'Programming reload of {0} when idle.'.format(
                event.pathname))

        GLib.idle_add(self.on_file_modify_callback, event)

    def on_file_modify_callback(self, event):
        ''' Reload file with a dedicated message. '''

        filename = event.pathname

        LOGGER.info('on_file_modify_callback({})'.format(filename))

        time.sleep(1)

        self.reload_file_contents(
            filename,
            '“{}” reloaded because of external change.'.format(
                filename))

        # Remove the callback from IDLE list.
        return False

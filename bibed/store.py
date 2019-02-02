import os
import time
import logging
import pyinotify

from threading import Lock

from bibed.foundations import (
    ldebug, lprint,
    lprint_caller_name,
    lprint_function_name,
    BibedException,
)

from bibed.constants import (
    DATA_STORE_LIST_ARGS,
    FILE_STORE_LIST_ARGS,
    BibAttrs,
    FSCols,
    FileTypes,
)

from bibed.preferences import memories
from bibed.database import BibedDatabase
from bibed.entry import BibedEntry

from bibed.gui.gtk import GLib, Gtk


LOGGER = logging.getLogger(__name__)


class PyinotifyEventHandler(pyinotify.ProcessEvent):

    app = None

    def process_IN_MODIFY(self, event):

        if __debug__:
            LOGGER.debug('Modify event start ({}).'.format(event.pathname))

        PyinotifyEventHandler.app.on_file_modify(event)

        if __debug__:
            LOGGER.debug('Modify event end ({}).'.format(event.pathname))

        return True


class BibedDataStoreException(BibedException):
    pass


class BibedFileStoreException(BibedException):
    pass


class AlreadyLoadedException(BibedFileStoreException):
    pass


class NoDatabaseForFilename(BibedFileStoreException):
    pass


class BibKeyNotFound(BibedException):
    pass


class BibedFileStoreNoWatchContextManager:
    ''' A simple context manager to temporarily disable inotify watches. '''

    def __init__(self, store, filename):
        self.store = store
        self.filename = filename
        self.reenable_inotify = True

    def __enter__(self):

        # assert lprint_caller_name()

        try:
            self.store.inotify_remove_watch(self.filename)

        except KeyError:
            # When called from store.close_file(),
            # the inotify watch has already been removed.
            self.reenable_inotify = False

        self.store.file_write_lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):

        # assert lprint_caller_name()

        self.store.file_write_lock.release()

        if self.reenable_inotify:
            self.store.inotify_add_watch(self.filename)


class BibedFileStore(Gtk.ListStore):
    ''' Stores filenames and BIB databases. '''

    def __init__(self, data_store):
        super().__init__(*FILE_STORE_LIST_ARGS)

        assert(isinstance(data_store, BibedDataStore))

        # cached number of files.
        self.num_user   = 0
        self.num_system = 0

        # BibedDatabase(s), linked to filenames
        self.databases = {}

        # A reference to the datastore,
        # to handle system files internally.
        self.data_store = data_store

        # Global lock to avoid concurrent writes,
        # which are destructive on flat files.
        self.file_write_lock = Lock()

        # Stores the GLib.idle_add() source.
        self.save_trigger_source = None

        self.setup_inotify()

    def __len__(self):

        # assert lprint_function_name()

        return self.num_user

    def lock(self, blocking=True):

        # assert lprint_function_name()
        # assert lprint(blocking)

        self.file_write_lock.acquire(blocking=blocking)

    def unlock(self):

        # assert lprint_function_name()

        try:
            self.file_write_lock.release()

        except Exception as e:
            LOGGER.exception(e)

    # ————————————————————————————————————————————————————————————————— Inotify

    def setup_inotify(self):

        # assert lprint_function_name()

        PyinotifyEventHandler.app = self

        self.wm = pyinotify.WatchManager()
        self.notifier = pyinotify.ThreadedNotifier(
            self.wm, PyinotifyEventHandler())
        self.notifier.start()

        self.wdd = {}

    def inotify_add_watch(self, filename):

        # assert lprint_function_name()
        # assert lprint(filename)

        self.wdd.update(self.wm.add_watch(filename, pyinotify.IN_MODIFY))

    def inotify_remove_watch(self, filename, delete=False):

        # assert lprint_caller_name(levels=2)
        # assert lprint_function_name()
        # assert lprint(filename)

        try:
            self.wm.rm_watch(self.wdd[filename])

        except KeyError:
            # Happens at close() when save() is called after the
            # inotify remove. I don't want to invert there, this
            # would produce resource-consuming off/on/off cycle.
            pass

        if delete:
            del self.wdd[filename]

    def on_file_modify(self, event):
        ''' Acquire lock and launch delayed updater. '''

        # assert lprint_function_name()
        # assert lprint(event)

        if self.file_write_lock.acquire(blocking=False) is False:
            # This occurs mainly if many inotify events come at once.
            # In rare cases we could be writing while an external change occurs.
            # This would be too bad. But having one lock per file is too much.
            return

        assert ldebug('Programming reload of {0} when idle.', event.pathname)

        GLib.idle_add(self.on_file_modify_callback, event)

    def on_file_modify_callback(self, event):
        ''' Reload file with a dedicated message. '''

        # assert lprint_function_name()

        filename = event.pathname

        # assert lprint(filename)

        time.sleep(1)

        self.reload(
            filename,
            '“{}” reloaded because of external change.'.format(
                filename))

        # Remove the callback from IDLE list.
        return False

    def no_watch(self, filename):

        # assert lprint_function_name()

        return BibedFileStoreNoWatchContextManager(self, filename)

    # ————————————————————————————————————————————————————————————————— Queries

    def has(self, filename):

        # assert lprint_function_name()
        # assert lprint(filename)

        for row in self:
            if row[0] == filename:
                return True

        return False

    def get_open_filenames(self, filetype=None):

        # assert lprint_function_name()
        # assert lprint(filetype)

        if filetype is None:
            filetype = FileTypes.USER

        return [
            row[FSCols.FILENAME]
            for row in self
            if row[FSCols.FILETYPE] == filetype
        ]

    def has_bib_key(self, key):

        # assert lprint_function_name()
        # assert lprint(key)

        for filename, database in self.databases.items():

            for entry in database.itervalues():
                if key == entry.key:
                    return filename

                # look in aliases (valid old key values) too.
                if key in entry.get_field('ids', '').split(','):
                    return filename

        return None

    def get_entry_by_key(self, key, filename=None):

        # assert lprint_function_name()
        # assert lprint(key, filename)

        if filename is None:
            for filename, database in self.databases.items():
                try:
                    database.get_entry_by_key(key)

                except KeyError:
                    # We must test all databases prior to raising “not found”.
                    pass

            raise BibKeyNotFound

        else:
            try:
                return self.databases[filename].get_entry_by_key(key)

            except KeyError:
                raise BibKeyNotFound

    def get_database(self, filename):

        # assert lprint_function_name()

        try:
            return self.databases[filename]

        except KeyError:
            raise NoDatabaseForFilename

    # ————————————————————————————————————————————————————————— File operations

    def parse(self, filename, recompute=True):
        ''' Internal method. '''

        # assert lprint_function_name()
        # assert lprint(filename, recompute)

        database = BibedDatabase(filename, self)

        self.databases[filename] = database

        for entry in database.values():
            self.data_store.append(entry.to_list_store_row())

        if recompute:
            self.data_store.do_recompute_global_ids()

    def load(self, filename, filetype=None, recompute=True):

        # assert lprint_function_name()
        # assert lprint(filename, filetype, recompute)

        if filename in self.databases:
            raise AlreadyLoadedException

        if filetype is None:
            filetype = FileTypes.USER

        self.parse(filename, recompute=recompute)

        self.inotify_add_watch(filename)

        if filetype == FileTypes.USER:
            self.num_user += 1

            if self.num_user == 2:
                self.prepend(('All', FileTypes.ALL, ))

        else:
            self.num_system += 1

        # Append to the store as last operation, for
        # everything to be ready for the interface signals.
        # Without this, window title fails to update properly.
        self.append((filename, filetype, ))

        memories.add_open_file(filename)
        memories.add_recent_file(filename)

    def save(self, thing):

        # assert lprint_function_name()

        if isinstance(thing, BibedEntry):
            database = thing.database

        elif isinstance(thing, BibedDatabase):
            database = thing

        elif isinstance(thing, str):
            database = self.databases[thing]

        filename = database.filename

        with self.no_watch(filename):
            database.write()

    def close(self, filename, save_before=True, recompute=True, remember_close=True):

        # assert lprint_function_name()
        # assert lprint(filename, save_before, recompute, remember_close)

        self.inotify_remove_watch(filename, delete=True)

        if save_before:
            # self.clear_save_callback()
            self.save(filename)

        self.clear_data(filename, recompute=recompute)

        filetype_index = FSCols.FILETYPE

        for row in self:
            if row[FSCols.FILENAME] == filename:
                if row[filetype_index] == FileTypes.USER:
                    self.num_user -= 1

                elif row[filetype_index] == FileTypes.SYSTEM:
                    self.num_system -= 1

                self.remove(row.iter)
                break

        # Remove the “All” special entry
        if self.num_user == 1:
            for row in self:
                if row[filetype_index] == FileTypes.ALL:
                    self.remove(row.iter)

        if remember_close:
            memories.remove_open_file(filename)

    def close_all(self, save_before=True, recompute=True, remember_close=True):

        for row in self:
            if row[FSCols.FILETYPE] not in (FileTypes.SYSTEM, FileTypes.USER):
                continue

            self.close(
                row[FSCols.FILENAME],
                save_before=save_before,
                recompute=recompute,
                remember_close=remember_close
            )

        try:
            self.notifier.stop()

        except Exception:
            pass

    def reload(self, filename):

        # assert lprint_function_name()

        # TODO: use a context manager to be sure we unlock.
        #       reloading could fail if file content is unparsable.

        # We try to re-lock to avoid conflict if reloading
        # manually while an inotify reload occurs.
        self.lock(blocking=False)

        # self.window.treeview.set_editable(False)
        self.close(filename,
                   save_before=False,
                   remember_close=False)

        result = self.load(filename)

        self.unlock()

        return result

    def clear_data(self, filename, recompute=True):
        ''' Clear the data store from one or more file contents. '''

        # assert lprint_function_name()
        # assert lprint(filename, recompute)

        if filename is None:
            # clear ALL user data (no system).
            for row in self:
                if row[FSCols.FILETYPE] == FileTypes.USER:
                    self.clear_data(row[FSCols.FILENAME])
            return

        # keep references handy for speed in loops.
        filename_index = BibAttrs.FILENAME
        store = self.data_store

        for row in store:
            if row[filename_index] == filename:
                    store.remove(row.iter)

        del self.databases[filename]

        if recompute:
            self.data_store.do_recompute_global_ids()

    def trigger_save(self, filename):
        ''' function called by anywhere in the code to trigger a save().

            This method acts as a proxy, can be called 10 times a second,
            and will just trigger *one* save operation one second after the
            first call.

        '''

        assert lprint_function_name()
        # assert lprint(filename)

        if self.file_write_lock.acquire(blocking=False) is False:
            return

        assert ldebug('Programming save of {0} in 1 second.', filename)

        self.save_trigger_source = GLib.idle_add(
            self.save_trigger_callback, filename)

    def save_trigger_callback(self, filename):

        assert lprint_function_name()

        time.sleep(1)

        # The trigger acquired the lock to avoid concurrent / parallel save().
        # We need to release to allow the database save() method to re-lock.
        self.file_write_lock.release()

        self.save(filename)

    def clear_save_callback(self):

        assert lprint_function_name()

        if self.save_trigger_source:
            # Remove the in-progress save()
            try:
                GLib.source_remove(self.save_trigger_source)

            except Exception:
                # The callback finished while we were blocked on the lock,
                # or GLib didn't automatically wipe self.save_trigger_source.
                pass


class BibedDataStore(Gtk.ListStore):

    def __init__(self, *args, **kwargs):
        super().__init__(
            *DATA_STORE_LIST_ARGS
        )

        # TODO: detect aliased fields and set self.use_aliased fields.

        pass

    def do_recompute_global_ids(self):

        # assert lprint_function_name()

        counter = 1
        global_id = BibAttrs.GLOBAL_ID

        for row in self:
            row[global_id] = counter
            counter += 1

    def insert_entry(self, entry):

        assert lprint_function_name()

        self.append(
            entry.to_list_store_row()
        )

        self.do_recompute_global_ids()

        assert ldebug('Row created with entry {}.', entry.key)

    def update_entry(self, entry):

        assert lprint_function_name()

        for row in self:
            if row[BibAttrs.GLOBAL_ID] == entry.gid:
                # This is far from perfect, we could just update the row.
                # But I'm tired and I want a simple way to view results.
                # TODO: do better on next code review.

                self.insert_after(row.iter, entry.to_list_store_row())
                self.remove(row.iter)

                assert ldebug(
                    'Row {} (entry {}) updated.',
                    row[BibAttrs.GLOBAL_ID], entry.key
                )

                break

import os
import time
import logging
import pyinotify

from threading import RLock

from bibed.foundations import (
    ldebug, lprint,
    lprint_caller_name,
    lprint_function_name,
)

from bibed.constants import (
    DATA_STORE_LIST_ARGS,
    FILE_STORE_LIST_ARGS,
    BibAttrs,
    FSCols,
    FileTypes,
    FILETYPES_COLORS,
    BIBED_SYSTEM_QUEUE_NAME,
    BIBED_SYSTEM_TRASH_NAME,
)

from bibed.foundations import touch_file
from bibed.exceptions import (
    AlreadyLoadedException,
    FileNotFoundError,
    BibKeyNotFoundError,
    NoDatabaseForFilenameError,
)
from bibed.utils import get_bibed_user_dir
from bibed.preferences import memories
from bibed.database import BibedDatabase
from bibed.entry import BibedEntry

from bibed.gtk import Gio, GLib, Gtk


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

    def __init__(self):
        super().__init__(*FILE_STORE_LIST_ARGS)

        # cached number of files.
        self.num_user   = 0
        self.num_system = 0

        # BibedDatabase(s), linked to filenames
        self.databases = {}

        # A reference to the datastore,
        # to handle system files internally.
        # Will be fille by data_store.__init__()
        self.data_store = None

        # Global lock to avoid concurrent writes,
        # which are destructive on flat files.
        self.file_write_lock = RLock()

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

    # ———————————————————————————————————————————————————————————— System files

    def load_system_files(self):

        # assert lprint_function_name()

        bibed_user_dir = get_bibed_user_dir()

        for filename, filetype in (
            (BIBED_SYSTEM_QUEUE_NAME, FileTypes.QUEUE),
            (BIBED_SYSTEM_TRASH_NAME, FileTypes.TRASH),
        ):

            full_pathname = os.path.join(bibed_user_dir, filename)

            if not os.path.exists(full_pathname):
                touch_file(full_pathname)

            self.load(full_pathname, filetype)

    def trash_entries(self, entries):
        '''
            :param entries: an iterable of :class:`~bibed.entry.BibedEntry`.
        '''
        # assert lprint_function_name()

        trash_database = self.get_database(filetype=FileTypes.TRASH)
        databases_to_write = set((trash_database, ))

        for entry in entries:
            entry.set_trashed()

            # Note the database BEFORE the move(), because
            # after move(), its the trash database.
            databases_to_write.add(entry.database)

            entry.database.move_entry(entry, trash_database)

        for database in databases_to_write:
            database.write()

    def untrash_entries(self, entries):

        assert lprint_function_name()

        trash_database = self.get_database(filetype=FileTypes.TRASH)
        databases_to_write = set((trash_database, ))
        databases_to_unload = set()

        for entry in entries:
            trashed_from, trashed_date = entry.trashed_informations

            # wipe trash-related informations.
            entry.set_trashed(False)

            try:
                database = self.get_database(filename=trashed_from)

            except NoDatabaseForFilenameError:
                # Database is not loaded.

                # Load without remembering, without affecting GUI.
                self.load(filename=trashed_from,
                          filetype=FileTypes.TRANSIENT)

                database = self.get_database(filename=trashed_from)

                databases_to_unload.add(database)

            trash_database.move_entry(entry, database)

            databases_to_write.add(database)

        for database in databases_to_write:
            database.write()

        for database in databases_to_unload:
            self.close(database.filename)

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

            raise BibKeyNotFoundError

        else:
            try:
                return self.databases[filename].get_entry_by_key(key)

            except KeyError:
                raise BibKeyNotFoundError

    def get_database(self, filename=None, filetype=None):
        ''' Get a database, either for a filename *or* a filetype. '''

        # assert lprint_function_name()

        assert (
            filename is None and filetype is not None
        ) or (
            filename is not None and filetype is None
        )
        assert filetype is None or (
            filetype is not None and filetype in (
                FileTypes.TRASH, FileTypes.QUEUE,
            )
        )

        if filetype is None:
            try:
                return self.databases[filename]

            except KeyError:
                raise NoDatabaseForFilenameError

        filename_index = FSCols.FILENAME
        filetype_index = FSCols.FILETYPE

        for row in self:
            if row[filetype_index] == filetype:
                return self.databases[row[filename_index]]

        raise NoDatabaseForFilenameError

    def get_filetype(self, filename):

        for row in self:
            if row[FSCols.FILENAME] == filename:
                return row[FSCols.FILETYPE]

        raise FileNotFoundError
    # ————————————————————————————————————————————————————————— File operations

    def parse(self, filename, filetype, impact_data_store=True, recompute=True):
        ''' Internal method. '''

        # assert lprint_function_name()
        # assert lprint(filename, recompute)

        database = BibedDatabase(filename, filetype, self)

        self.databases[filename] = database

        if impact_data_store:
            for entry in database.values():
                self.data_store.append(entry, filetype)

            # Don't bother recompute if data_store is not impacted.
            if recompute:
                self.data_store.do_recompute_global_ids()

    def load(self, filename, filetype=None, recompute=True):

        # assert lprint_function_name()
        # assert lprint(filename, filetype, recompute)

        if filename in self.databases:
            raise AlreadyLoadedException

        if filetype is None:
            filetype = FileTypes.USER

        inotify = True
        impact_data_store = True

        # Transient files don't get to the datastore.
        if filetype == FileTypes.TRANSIENT:
            impact_data_store = False
            recompute = False
            inotify = False

        self.parse(filename, filetype,
                   impact_data_store=impact_data_store,
                   recompute=recompute)

        if inotify:
            self.inotify_add_watch(filename)

        if filetype == FileTypes.USER:
            self.num_user += 1

            if self.num_user == 2:
                self.prepend(('—', FileTypes.SEPARATOR, ))
                self.prepend(('All', FileTypes.ALL, ))

        elif filetype & FileTypes.SYSTEM:
            self.num_system += 1

        # Append to the store as last operation, for
        # everything to be ready for the interface signals.
        # Without this, window title fails to update properly.
        self.append((filename, filetype, ))

        if not filetype & FileTypes.SYSTEM:
            memories.add_open_file(filename)
            memories.add_recent_file(filename)

    def save(self, thing):

        # assert lprint_function_name()
        # assert lprint(thing)

        if isinstance(thing, BibedEntry):
            database = thing.database

        elif isinstance(thing, BibedDatabase):
            database = thing

        elif isinstance(thing, str):
            database = self.databases[thing]

        database.write()

    def close(self, filename, save_before=True, recompute=True, remember_close=True):

        # assert lprint_function_name()
        # assert lprint(filename, save_before, recompute, remember_close)

        filetype_index = FSCols.FILETYPE
        impact_data_store = True
        row_to_remove = None
        inotify = True

        for row in self:
            if row[FSCols.FILENAME] == filename:
                if row[filetype_index] == FileTypes.USER:
                    self.num_user -= 1

                elif row[filetype_index] == FileTypes.SYSTEM:
                    self.num_system -= 1

                elif row[filetype_index] == FileTypes.TRANSIENT:
                    impact_data_store = False
                    recompute = False
                    inotify = False

                row_to_remove = row
                break

        if inotify:
            self.inotify_remove_watch(filename, delete=True)

        if save_before:
            # self.clear_save_callback()
            self.save(filename)

        self.remove(row_to_remove.iter)

        if impact_data_store:
            self.clear_data(filename, recompute=recompute)

        # Remove the “All” special entry
        if self.num_user == 1:
            for row in self:
                if row[filetype_index] == FileTypes.ALL:
                    # remove the separator, then “All”
                    self.remove(self.iter_next(row.iter))
                    self.remove(row.iter)

                    # Then exit, else store goes mad looping on None.
                    break

        if impact_data_store and remember_close:
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

        column_filetype = FSCols.FILETYPE
        column_filename = FSCols.FILENAME

        if filename is None:
            # clear ALL USER data (no system).
            for row in self:
                if row[column_filetype] == FileTypes.USER:
                    self.clear_data(row[column_filename], recompute=recompute)
            return

        # keep references handy for speed in loops.
        self.data_store.clear_data(filename, recompute=recompute)

        del self.databases[filename]

    def trigger_save(self, filename):
        ''' function called by anywhere in the code to trigger a save().

            This method acts as a proxy, can be called 10 times a second,
            and will just trigger *one* save operation one second after the
            first call.

        '''

        # assert lprint_function_name()
        # assert lprint(filename)

        if self.file_write_lock.acquire(blocking=False) is False:
            return

        # Useless, everything runs too fast.
        # self.clear_save_callback()

        assert ldebug('Programming save of {0} when idle.', filename)

        self.save_trigger_source = GLib.idle_add(
            self.save_trigger_callback, filename)

    def save_trigger_callback(self, filename):

        # assert lprint_function_name()

        # time.sleep(1)

        self.save(filename)

        # The trigger acquired the lock to avoid concurrent / parallel save().
        # We need to release to allow the database save() method to re-lock.
        self.file_write_lock.release()

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

        self.files_store = kwargs.pop('files_store', None)

        assert self.files_store is not None

        self.files_store.data_store = self

    def __entry_to_store(self, entry, filetype=None):
        ''' Convert a BIB entry, to fields for a Gtk.ListStore. '''

        # `BibedEntry`.`bibtexparser_entry` (eg. dict)
        entry_fields = entry.entry

        if filetype is None:
            filetype = self.files_store.get_filetype(entry.database.filename)

        return (
            entry.gid,  # global_id, computed by app.
            entry.database.filename,
            entry.index,  # TODO: remove this field, everywhere.
            entry.tooltip,
            entry.type,
            entry.key,
            entry_fields.get('file', ''),
            entry_fields.get('url', ''),
            entry_fields.get('doi', ''),
            GLib.markup_escape_text(entry.author),
            GLib.markup_escape_text(entry_fields.get('title', '')),
            entry_fields.get('subtitle', ''),
            GLib.markup_escape_text(entry.journal),
            entry.year,
            entry_fields.get('date', ''),
            entry.quality,
            entry.read_status,
            entry.comment,
            filetype,
            FILETYPES_COLORS[filetype],
        )

    def do_recompute_global_ids(self):

        # assert lprint_function_name()

        counter = 1
        gid_index = BibAttrs.GLOBAL_ID

        for row in self:
            row[gid_index] = counter
            counter += 1

    def append(self, entry, filetype=None):

        return super().append(self.__entry_to_store(entry, filetype))

    def insert_entry(self, entry):

        # assert lprint_function_name()

        iter = self.append(entry)

        self.do_recompute_global_ids()

        if __debug__:
            row = self[iter]

            ldebug('Row {} created with entry {}.',
                   row[BibAttrs.GLOBAL_ID], entry.key)

    def update_entry(self, entry):

        # assert lprint_function_name()

        assert entry.gid >= 0

        gid_index = BibAttrs.GLOBAL_ID

        for row in self:
            if row[gid_index] == entry.gid:
                # This is far from perfect, we could just update the row.
                # But I'm tired and I want a simple way to view results.
                # TODO: do better on next code review.

                self.insert_after(row.iter, self.__entry_to_store(entry))
                self.remove(row.iter)

                assert ldebug(
                    'Row {} updated (entry {}).',
                    row[gid_index], entry.key
                )

                break

    def delete_entry(self, entry):

        # assert lprint_function_name()

        assert entry.gid >= 0

        gid_index = BibAttrs.GLOBAL_ID

        for row in self:
            if row[gid_index] == entry.gid:
                self.remove(row.iter)

        self.do_recompute_global_ids()

        assert ldebug('Row {} deleted (was entry {}).',
                      row[gid_index], entry.key)

    def clear_data(self, filename, recompute=True):

        # assert lprint_function_name()

        column_filename = BibAttrs.FILENAME

        for row in self:
            if row[column_filename] == filename:
                    self.remove(row.iter)

        if recompute:
            self.do_recompute_global_ids()

import os
import time
import logging
import pyinotify

from threading import RLock

from bibed.exceptions import (
    AlreadyLoadedException,
    FileNotFoundError,
    BibKeyNotFoundError,
    NoDatabaseForDBIDError,
    NoDatabaseForFilenameError,
)

from bibed.ltrace import (  # NOQA
    ldebug, lprint,
    lprint_caller_name,
    lprint_function_name,
)

from bibed.constants import (
    BibAttrs,
    FileTypes,
    FILETYPES_COLORS,
    BIBED_SYSTEM_IMPORTED_NAME,
    BIBED_SYSTEM_QUEUE_NAME,
    BIBED_SYSTEM_TRASH_NAME,
)

from bibed.system import touch_file
from bibed.user import get_bibed_user_dir
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
            # When called from store.close_database(),
            # the inotify watch has already been removed.
            self.reenable_inotify = False

        self.store.file_write_lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):

        # assert lprint_caller_name()

        self.store.file_write_lock.release()

        if self.reenable_inotify:
            self.store.inotify_add_watch(self.filename)


class BibedFileStore(Gio.ListStore):
    ''' Stores filenames and BIB databases.


        .. warning:: never override :meth:`__len__` to alter the real number of
            items in self, because GObject iteration process relies on the
            real value. That's why we've got `num_user` and `num_system`.
    '''

    def __init__(self):
        super().__init__()

        # cached number of files.
        self.num_user   = 0
        self.num_system = 0

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
            (BIBED_SYSTEM_IMPORTED_NAME, FileTypes.IMPORTED),
            (BIBED_SYSTEM_QUEUE_NAME, FileTypes.QUEUE),
            (BIBED_SYSTEM_TRASH_NAME, FileTypes.TRASH),
        ):

            full_pathname = os.path.join(bibed_user_dir, filename)

            if not os.path.exists(full_pathname):
                touch_file(full_pathname)

            # load() returns a database.
            self.load(full_pathname, filetype).selected = False

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

        trash_database = self.trash
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

        LOGGER.debug('Programming reload of {0} when idle.'.format(
                     event.pathname))

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
            if row.filename == filename:
                return True

        return False

    def get_open_filenames(self, filetype=None):

        # assert lprint_function_name()
        # assert lprint(filetype)

        if filetype is None:
            filetype = FileTypes.USER

        return [
            db.filename
            for db in self
            if db.filetype == filetype
        ]

    def has_bib_key(self, key):

        # assert lprint_function_name()
        # assert lprint(key)

        for database in self:

            for entry in database.itervalues():
                if key == entry.key:
                    return database.filename

                # look in aliases (valid old key values) too.
                if key in entry.get_field('ids', '').split(','):
                    return database.filename

        return None

    def get_entry_by_key(self, key, dbid=None):

        # assert lprint_function_name()
        # assert lprint(key, filename)

        if dbid is None:
            for database in self:
                try:
                    return database.get_entry_by_key(key)

                except KeyError:
                    # We must test all databases prior to raising “not found”.
                    pass

            raise BibKeyNotFoundError

        else:
            try:
                return self.get_database(dbid=dbid).get_entry_by_key(key)

            except NoDatabaseForFilenameError:
                raise BibKeyNotFoundError

    def get_database(self, filename=None, filetype=None, dbid=None):
        ''' Get a database, either for a filename *or* a filetype. '''

        # assert lprint_function_name()

        assert (
            filename is not None
            or filetype is not None
            or dbid is not None
        )

        assert filetype is None or filetype in (
            FileTypes.TRASH,
            FileTypes.QUEUE,
            FileTypes.IMPORTED,
        )

        if filetype is None:
            if dbid:
                for database in self:
                    if database.objectid == dbid:
                        return database

                raise NoDatabaseForDBIDError(dbid)

            else:
                for database in self:
                    if database.filename == filename:
                        return database

                raise NoDatabaseForFilenameError(filename)

        for database in self:
            if database.filetype == filetype:
                return database

        raise NoDatabaseForFilenameError(filetype)

    def get_filetype(self, filename):

        for database in self:
            if database.filename == filename:
                return database.filetype

        raise FileNotFoundError

    def sync_selection(self, selected_databases):

        # assert lprint('SYNC SELECTION', [x.filename for x in selected_databases])

        for database in self:
            database.selected = bool(database in selected_databases)

        # assert lprint('AFTER SYNC', [str(db) for db in self])
        pass

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def system_databases(self):

        for database in self:
            if database.filetype & FileTypes.SYSTEM:
                yield database

    @property
    def selected_system_databases(self):

        for database in self:
            if database.filetype & FileTypes.SYSTEM and database.selected:
                yield database

    @property
    def user_databases(self):

        for database in self:
            if database.filetype & FileTypes.USER:
                yield database

    @property
    def selected_user_databases(self):

        for database in self:
            if database.filetype & FileTypes.USER and database.selected:
                yield database

    @property
    def selected_databases(self):

        for database in self:
            if database.selected:
                yield database

    @property
    def trash(self):

        for database in self:
            if database.filetype & FileTypes.TRASH:
                return database

    @property
    def queue(self):

        for database in self:
            if database.filetype & FileTypes.QUEUE:
                return database

    @property
    def imported(self):

        for database in self:
            if database.filetype & FileTypes.IMPORTED:
                return database

    # ————————————————————————————————————————————————————————— File operations

    def load(self, filename, filetype=None):

        # assert lprint_function_name()
        # assert lprint(filename, filetype)

        if self.has(filename):
            raise AlreadyLoadedException

        if filetype is None:
            filetype = FileTypes.USER

        inotify = True
        impact_data_store = True

        # Transient files don't get to the datastore.
        if filetype == FileTypes.TRANSIENT:
            impact_data_store = False
            inotify = False

        database = BibedDatabase(filename, filetype)

        if impact_data_store:
            for entry in database.values():
                self.data_store.append(entry)

        if inotify:
            self.inotify_add_watch(filename)

        if filetype == FileTypes.USER:
            self.num_user += 1

        elif filetype & FileTypes.SYSTEM:
            self.num_system += 1

        # Append to the store as last operation, for
        # everything to be ready for the interface signals.
        # Without this, window title fails to update properly.
        self.append(database)

        LOGGER.debug('Loaded database “{}”.'.format(filename))

        if not filetype & FileTypes.SYSTEM:
            memories.add_open_file(filename)
            memories.add_recent_file(filename)

        return database

    def save(self, thing):

        # assert lprint_function_name()
        # assert lprint(thing)

        if isinstance(thing, BibedEntry):
            database_to_write = thing.database

            assert database_to_write is not None, 'Entry has no database!'

        elif isinstance(thing, BibedDatabase):
            database_to_write = thing

        elif isinstance(thing, str):
            database_to_write = self.get_database(filename=thing)

        else:
            raise NotImplementedError(type(thing))

        database_to_write.write()

    def close(self, db_to_close, save_before=True, remember_close=True):

        # assert lprint_function_name()
        # assert lprint(filename, save_before, remember_close)

        database_to_remove = None
        index_to_remove = None
        impact_data_store = True
        inotify = True

        for index, database in enumerate(self):

            if database == db_to_close:
                if database.filetype == FileTypes.USER:
                    self.num_user -= 1

                elif database.filetype == FileTypes.SYSTEM:
                    self.num_system -= 1

                elif database.filetype == FileTypes.TRANSIENT:
                    impact_data_store = False
                    inotify = False

                database_to_remove = database
                index_to_remove = index
                break

        if inotify:
            self.inotify_remove_watch(database_to_remove.filename, delete=True)

        if save_before:
            # self.clear_save_callback()
            self.save(database_to_remove)

        assert database_to_remove is not None

        self.remove(index_to_remove)

        if __debug__:
            LOGGER.debug('Closed database “{}”.'.format(database_to_remove))

        if impact_data_store:
            self.clear_data(database_to_remove)

        if impact_data_store and remember_close:
            memories.remove_open_file(database_to_remove.filename)

        del database_to_remove, db_to_close

    def close_all(self, save_before=True, remember_close=True):

        # Again, still, copy()/slice() self to avoid misses.
        for index, database in enumerate(self[:]):
            if database.filetype not in (FileTypes.SYSTEM, FileTypes.USER):
                continue

            self.close(
                database,
                save_before=save_before,
                remember_close=remember_close
            )

        try:
            self.notifier.stop()

        except Exception:
            pass

    def reload(self, database):

        # assert lprint_function_name()

        # TODO: use a context manager to be sure we unlock.
        #       reloading could fail if file content is unparsable.

        # We try to re-lock to avoid conflict if reloading
        # manually while an inotify reload occurs.
        self.lock(blocking=False)

        filename = database.filename

        # self.window.treeview.set_editable(False)
        self.close(database,
                   save_before=False,
                   remember_close=False)

        result = self.load(filename)

        self.unlock()

        return result

    def clear_data(self, database=None):
        ''' Clear the data store from one or more file contents. '''

        # assert lprint_function_name()
        # assert lprint(filename)

        if database is None:
            # clear all USER data only (no system).
            for database in self:
                if database.filetype == FileTypes.USER:
                    self.data_store.clear_data(database)

        else:
            self.data_store.clear_data(database)


class BibedDataStore(Gtk.ListStore):

    #
    # TODO: convert BibedEntry to a GObject subclass and simplify all of this.
    #

    def __init__(self, *args, **kwargs):

        super().__init__(
            *BibAttrs.as_store_args
        )

        self.files_store = kwargs.pop('files_store', None)

        assert self.files_store is not None

        self.files_store.data_store = self

        BibedDatabase.data_store = self
        BibedDatabase.files_store = self.files_store
        BibedEntry.files_store = self.files_store

    def __str__(self):
        return 'BibedDataStore'

    def __entry_to_store(self, entry):
        ''' Convert a BIB entry, to fields for a Gtk.ListStore. '''

        return (
            entry.database.objectid,
            entry.database.filetype,
            FILETYPES_COLORS[entry.database.filetype],
            entry.col_tooltip,
            entry.type,
            entry.key,
            entry.get_field('file', ''),
            entry.get_field('url', ''),
            entry.get_field('doi', ''),
            entry.col_author,
            entry.col_title,
            entry.col_subtitle,
            entry.col_in_or_by,
            entry.year,
            entry.get_field('date', ''),
            entry.quality,
            entry.read_status,
            entry.comment,
            ','.join(entry.keywords),  # flatten for search / filter.
        )

    def append(self, entry):

        return super().append(self.__entry_to_store(entry))

    def add_entry(self, entry):

        # assert lprint_function_name()

        iter = self.append(entry)

        index = self.get_path(iter)

        LOGGER.debug('Row {} created with entry {}.'.format(index, entry.key))

    def update_entry(self, entry, fields=None):

        # assert lprint_function_name()

        key_col = BibAttrs.KEY
        key_to_update = entry.key
        index = None

        for index, row in enumerate(self):
            if row[key_col] == key_to_update:
                if fields:
                    for key, value in fields.items():
                        row[key] = value
                else:
                    for index, value in enumerate(self.__entry_to_store(entry)):
                        row[index] = value

                break

        LOGGER.debug('Row {} updated (entry {}{}).'.format(
                     index, entry.key,
                     ', fields={}'.format(fields) if fields else ''))

    def delete_entry(self, entry):

        # assert lprint_function_name()

        key_to_delete = entry.key
        key_col = BibAttrs.KEY
        index = None

        for index, row in enumerate(self):
            if row[key_col] == key_to_delete:
                self.remove(row.iter)
                break

        LOGGER.debug('Row {} deleted (was entry {}).'.format(
                     index, entry.key))

    def clear_data(self, database):

        # assert lprint_function_name()

        db_col = BibAttrs.DBID
        db_id = database.objectid

        iters_to_remove = []

        for row in self:
            if row[db_col] == db_id:
                iters_to_remove.append(row.iter)

        for iter in iters_to_remove:
            self.remove(iter)

        LOGGER.debug('Cleared data for {}.'.format(database))

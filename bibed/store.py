import os
import logging
import pyinotify

from threading import Timer, Event

from bibed.exceptions import (
    AlreadyLoadedException,
    FileNotFoundError,
    BibKeyNotFoundError,
    NoDatabaseForDBIDError,
    NoDatabaseForFilenameError,
    NoSystemDatabaseError,
)

from bibed.ltrace import (  # NOQA
    ldebug, lprint, lcolorize,
    lprint_function_name,
    lprint_caller_name,
)

from bibed.constants import (
    BibAttrs,
    FileTypes,
    BIBED_SYSTEM_IMPORTED_NAME,
    BIBED_SYSTEM_QUEUE_NAME,
    BIBED_SYSTEM_TRASH_NAME,
)

from bibed.system import touch_file
from bibed.user import get_bibed_user_dir
from bibed.preferences import memories
from bibed.database import BibedDatabase
from bibed.entry import BibedEntry

from bibed.gtk import Gio, Gtk


LOGGER = logging.getLogger(__name__)


class PyinotifyEventHandler(pyinotify.ProcessEvent):

    store = None

    def process_IN_MODIFY(self, event):

        # if __debug__:
        #     LOGGER.debug(lcolorize(
        #         'Modify event start ({}).'.format(event.pathname)))

        PyinotifyEventHandler.store.on_file_modify(event)

        # if __debug__:
        #     LOGGER.debug(lcolorize(
        #         'Modify event end ({}).'.format(event.pathname)))

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

        # We are writing a file, block everyone.
        self.store.is_usable.clear()

    def __exit__(self, exc_type, exc_val, exc_tb):

        # assert lprint_caller_name()

        # It's OK now, folks!
        self.store.is_usable.set()

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

        # == controllers.data
        self.data = None

        # cached number of files.
        self.num_user   = 0
        self.num_system = 0

        # Global event to avoid writing files while they
        # need to be reloaded, or that sort of things.
        self.is_usable = Event()
        self.is_usable_timer = None

        # We can always use files, except in rare moments where they are
        # written / modified by another process. See importer.py and
        # on_file_modify() method for details.
        self.is_usable.set()

        # Stores the GLib.idle_add() source.
        self.save_trigger_source = None

        BibedDatabase.files = self
        BibedEntry.files = self

        self.setup_inotify()

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
        ''' Instanciate a :class:`~pyinotify.WatchManager` and a
            :class:`~pyinotify.ThreadedNotifier` with a
            :class:`PyinotifyEventHandler` instance.
        '''
        # assert lprint_function_name()

        PyinotifyEventHandler.store = self

        self.wm = pyinotify.WatchManager()
        self.notifier = pyinotify.ThreadedNotifier(self.wm,
                                                   PyinotifyEventHandler())
        self.notifier.start()

        self.wdd = {}

    def inotify_add_watch(self, filename):

        # assert lprint_function_name(filename=filename)

        self.wdd.update(self.wm.add_watch(filename, pyinotify.IN_MODIFY))

    def inotify_remove_watch(self, filename, delete=False):

        # assert lprint_caller_name(levels=2)
        # assert lprint_function_name(filename=filename, delete=delete)

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
        ''' Notify store unusable and launch delayed reloader. '''

        # assert lprint_function_name(pathname=event.pathname)

        # The other (main or background) process will try to use the system
        # files too soon (as soon as messages are received).
        # We need to make it wait until last MODIFY inotify event has settled.

        self.is_usable.clear()

        if self.is_usable_timer is not None:
            self.is_usable_timer.cancel()

            LOGGER.debug(
                f'RE-programming reload of {event.pathname} in a little while.')

        else:
            LOGGER.debug(
                f'Programming reload of {event.pathname} in a little while.')

        self.is_usable_timer = Timer(
            1.0, self.on_file_modify_callback, args=(event, )
        )
        self.is_usable_timer.start()

    def on_file_modify_callback(self, event):
        ''' Reload file with a dedicated message. '''

        # assert lprint_function_name(filename=event.pathname)

        self.reload(self.get_database(filename=event.pathname, wait=False))

        # Now that file is reloaded, signify files are usable.
        self.is_usable.set()
        self.is_usable_timer = None

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

    def get_database(self, filename=None,
                     filetype=None, dbid=None,
                     auto_load=False, wait=True):
        ''' Get a database, either for a filename *or* a filetype.

            :param wait: should the method wait for `is_usable` or not. There
                is only **one** case where it should not: when files are
                already unusable and the current call is done in the inotify
                callback that's run to make them usable again.
        '''

        # assert lprint_function_name(filename=filename, filetype=filetype,
        #                             dbid=dbid, auto_load=auto_load)

        # The current method is used a lot in messaging.
        # Wait as much as possible for the files to settle
        # before trying to get a database.
        if wait:
            self.is_usable.wait()

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

                if auto_load:
                    return self.load(filename)

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

        raise NoSystemDatabaseError('did you call controllers.files.load_system_files()?')

    @property
    def queue(self):

        for database in self:
            if database.filetype & FileTypes.QUEUE:
                return database

        raise NoSystemDatabaseError('did you call controllers.files.load_system_files()?')

    @property
    def imported(self):

        for database in self:
            if database.filetype & FileTypes.IMPORTED:
                return database

        raise NoSystemDatabaseError('did you call controllers.files.load_system_files()?')

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

        if impact_data_store and self.data is not None:
            for entry in database.values():
                self.data.append(entry)

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

    def close(self, db_to_close, save_before=False, remember_close=True):

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

        filename = database.filename
        selected = database.selected

        # In case we reload a system database
        # (this happens in background process)
        filetype = database.filetype

        # self.window.treeview.set_editable(False)
        self.close(database,
                   save_before=False,
                   remember_close=False)

        result = self.load(filename, filetype).selected = selected

        return result

    def clear_data(self, database=None):
        ''' Clear the data store from one or more file contents. '''

        # assert lprint_function_name()
        # assert lprint(filename)

        if self.data is None:
            # We are in the background process, no data_store.
            return

        if database is None:
            # clear all USER data only (no system).
            for database in self:
                if database.filetype == FileTypes.USER:
                    self.data.clear_data(database)

        else:
            self.data.clear_data(database)


class BibedDataStore(Gtk.ListStore):

    #
    # TODO: convert BibedEntry to a GObject subclass and simplify all of this.
    #

    def __init__(self, *args, **kwargs):

        super().__init__(
            *BibAttrs.as_store_args
        )

        controllers = kwargs.pop('controllers', None)

        if controllers is not None:
            controllers.files.data = self
            BibedDatabase.data = self

    def __str__(self):
        return 'BibedDataStore'

    def __entry_to_store(self, entry):
        ''' Convert a BIB entry, to fields for a Gtk.ListStore. '''

        return (
            entry.database.objectid,
            entry.database.filetype,

            # Entry displayed (or converted) data.
            entry.col_type,
            entry.key,
            entry.get_field('file', ''),
            entry.get_field('url', ''),
            entry.get_field('doi', ''),
            entry.col_author,
            entry.col_title,
            entry.col_in_or_by,
            entry.col_year,
            entry.col_quality,
            entry.col_read_status,
            entry.col_abstract_or_comment,

            # search-only fields.
            entry.col_subtitle,
            entry.col_comment,
            entry.col_keywords,
            entry.col_abstract,

            # completion fields.
            entry.comp_journaltitle,
            entry.comp_editor,
            entry.comp_publisher,
            entry.comp_series,
            entry.comp_type,
            entry.comp_howpublished,
            entry.comp_entrysubtype,

            # context.
            entry.context_color,
        )

    def append(self, entry):

        return super().append(self.__entry_to_store(entry))

    def add_entry(self, entry):

        # assert lprint_function_name()

        iter = self.append(entry)

        index = self.get_path(iter)

        LOGGER.debug('Row {} created with entry {}.'.format(index, entry.key))

    def update_entry(self, entry, fields=None, old_keys=None):

        # assert lprint_function_name()

        key_col = BibAttrs.KEY

        # NOTE: even if old_keys is an array, only ONE will be matched,
        #       because it's the one that have just been renamed.
        keys_to_update = [entry.key] if old_keys is None else old_keys
        index = None

        for index, row in enumerate(self):
            if row[key_col] in keys_to_update:
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


import os
import shutil
import datetime

import logging
import bibtexparser
from bibtexparser.bibdatabase import BibDatabase as BibtexParserDatabase

from bibed.exceptions import IndexingFailedError

from bibed.ltrace import (  # NOQA
    ldebug, lprint,
    lprint_caller_name,
    lprint_function_name,
)

from bibed.constants import FileTypes
from bibed.strings import friendly_filename
from bibed.preferences import gpod
from bibed.entry import BibedEntry
from bibed.gtk import GObject

LOGGER = logging.getLogger(__name__)


# ———————————————————————————————————————————————————————— Controller Classes

class BibedDatabase(GObject.GObject):
    ''' GOject subclass that wraps a :mod:`bibtexparser` database for faster
        access, higher-level operations between multiple databases, and updates
        to a same-level :class:`Gtk.ListStore`.

        Beiing a GObject subclass makes it directly usable in GTK GUI objects,
        which is not the less cool feature of it.
    '''

    # NOTE: https://stackoverflow.com/a/11180599/654755

    filename = GObject.property(type=str)
    filetype = GObject.property(type=int, default=FileTypes.USER)

    # Used in the GUI to know which file(s) is(are) selected.
    selected = GObject.property(type=bool, default=False)

    def __init__(self, filename, filetype, store):
        ''' Create a :class:`~bibed.database.BibedDatabase` instance.

            :param filename: a full pathname, as a string, for a `BibTeX` /
                `BibLaTeX` database.
            :param fileype: the application file type, from `FileTypes` enum. This is used in tooltips and other descriptive fields, to decide if full pathname or folder is shown or not.
            :param store: a :class:`~bibed.store.BibedFileStore` instance. its
                `.data_store` attribute will be kept handy in the current
                database attributes.
        '''

        # TODO: think about getting rid of the whole bibtexparser level.
        #       it's using memory, for nothing more than what we do.
        #       We could at least remove the entries after load,
        #       and rebuild them just for write(), like we do for
        #       _internal_* fields at the BibedEntry level.

        super().__init__()

        self.filename = filename
        self.filetype = filetype
        self.files_store = store
        self.data_store  = self.files_store.data_store

        # TODO: detect BibTeX aliased fields and set
        #       self.use_aliased fields or convert them.

        self.parser = bibtexparser.bparser.BibTexParser(
            ignore_nonstandard_types=False,
            interpolate_strings=False,
            common_strings=True,
        )

        self.writer = bibtexparser.bwriter.BibTexWriter()
        self.writer.indent = '    '

        try:
            with open(self.filename, 'r') as bibfile:
                self.bibdb = self.parser.parse_file(bibfile)

        except IndexError:
            # empty file (probably just created)
            self.bibdb = BibtexParserDatabase()

        # self.bibdb.comments
        # self.bibdb.preambles
        # self.bibdb.strings

        self.entries = {}

        for index, entry in enumerate(self.bibdb.entries):
            # Needs to be a tuple for re-indexation operations.
            self.entries[entry['ID']] = [entry, index]

    def __str__(self):

        return 'BibedDatabase({}[{}]{})'.format(
            os.path.basename(self.filename),
            self.filetype,
            ' SELECTED' if self.selected else '')

    def __len__(self):

        return len(self.entries)

    def __eq__(self, other):
        ''' Overrides the default implementation '''

        if isinstance(other, BibedDatabase):
            return self.filename == other.filename

        return NotImplemented

    def __hash__(self):
        ''' Make class set()-able. '''
        return hash(self.filename)

    def get_entry_by_key(self, key):

        # assert lprint_function_name()

        return BibedEntry(self, *self.entries[key])

    def keys(self):

        # assert lprint_function_name()

        return self.entries.keys()

    def itervalues(self):

        # assert lprint_function_name()

        for index, entry in enumerate(self.bibdb.entries):
            yield BibedEntry(self, entry, index)

    def values(self):

        # assert lprint_function_name()

        return [x for x in self.itervalues()]

    def add_entry(self, entry):
        ''' Add an entry into the current database.

            This operation will update underlying the Gtk datastore.

            .. note:: it's up to the caller to call :method:`write` on the
                database.
        '''

        # assert lprint_function_name()
        # assert lprint(entry)

        new_index = len(self.bibdb.entries)

        # Insert in BibedDatabase.
        # We need a tuple for later index assignments.
        self.entries[entry.key] = [entry.entry, new_index]

        # Idem in bibtexparser database.
        self.bibdb.entries.append(entry.entry)

        entry.index = new_index

        assert self.bibdb.entries.index(entry.entry) == new_index

        self.data_store.insert_entry(entry)

        if __debug__:
            LOGGER.debug('{0}.add_entry({1}) done.'.format(self, entry))

    def delete_entry(self, entry, old_index=None):
        ''' Delete an entry from the current database.

            This operation will update underlying the Gtk datastore.

            .. note:: it's up to the caller to call :method:`write` on the
                database.
        '''
        # assert lprint_function_name()
        # assert lprint(entry, entry.gid)

        assert entry.index >= 0
        assert entry.gid >= 0

        # old_index is set in case of a move.
        entry_index = entry.index if old_index is None else old_index

        # Here, or at the end?
        self.data_store.delete_entry(entry)

        del self.entries[entry.key]

        self.bibdb.entries.pop(entry_index)

        # NOTE: 20190203: the underlying dict is updated correctly,
        # but only the first time you call it. It's a one shot.
        # lprint(self.bibdb.entries_dict.keys())

        # decrement indexes of posterior entries
        for btp_entry in self.bibdb.entries[entry_index:]:

            # In rare cases (multiple deletion) the garbage collector does not
            # collect deleted keys fast enough. Thus we get() and handle the
            # situation gracefully.
            value = self.entries.get(btp_entry['ID'])
            try:
                value[1] -= 1

            except TypeError:
                pass

        assert self.check_indexes()

        if __debug__:
            LOGGER.debug('{0}.delete_entry({1}) done.'.format(self, entry))

    def move_entry(self, entry, destination_database, write=True):
        ''' Move an entry from a database to another.

            internally, this inserts the entry into the destination database,
            and then removes it from the source one. There could be some
            situations (application crash…) where the entry would be
            duplicated, or lost. Typically these situations have external
            causes.

            This operation will update underlying the Gtk datastore.

            :param entry: a :class:`~bibed.entry.BibedEntry` instance.
            :param destination_database: a :class:`bibed.database.BibedDatabase` instance.
            :param save: boolean, which can be disabled in case of multiple
                move operations, for the caller to merge write() calls and
                optimize resources consumption.
        '''

        # assert lprint_function_name()

        assert entry.gid >= 0

        # This is important for the delete operation to act
        # on the right database, else “self” could be the
        # destination and thus delete() just after add().
        source_database = entry.database

        # This is important, else GUI will still write in source database.
        entry.database = destination_database

        # save it before it gets overwritten by add_entry()
        old_index = entry.index

        # NOTE: this method does not update the data store, because
        #       add*() and delete*() methods already do what's needed.

        destination_database.add_entry(entry)
        source_database.delete_entry(entry, old_index)

        if write:
            destination_database.write()
            source_database.write()

        if __debug__:
            LOGGER.debug('{0}.move_entry({1}) to {2} done.'.format(
                source_database, entry, destination_database))

    def update_entry_key(self, entry):

        # assert lprint_function_name()
        # assert lprint(entry)

        # Note: update_entry_key() is a high-level operation. We
        #       do not touch the store. This will be done by caller.

        old_keys = [x.strip() for x in entry['ids'].split(',')]

        for old_key in old_keys:
            if old_key in self.keys():
                old_index = self.entries[old_key][1]
                break

        # delete and re-insert in BibedDatabase.
        del self.entries[old_key]
        self.entries[entry.key] = (entry.entry, old_index)

        # idem in bibtexparser database.
        del self.bibdb.entries[old_index]
        self.bibdb.entries.insert(old_index, entry.entry)

        if __debug__:
            LOGGER.debug('{0}.update_entry_key({1}) done.'.format(self, entry))

    def backup(self):

        # assert lprint_function_name()
        # assert lprint(self.filename)

        dirname = os.path.dirname(self.filename)
        basename = os.path.basename(self.filename)

        # Using microseconds in backup filename should avoid collisions.
        # Using time will also help for cleaning old backups.
        new_filename = os.path.join(
            dirname,
            # HEADS UP: backup file starts with a dot, it's hidden.
            '.{basename}.save.{datetime}.bib'.format(
                basename=basename.rsplit('.', 1)[0],
                datetime=datetime.datetime.now().isoformat(sep='_')
            )
        )

        try:
            shutil.copyfile(self.filename, new_filename)
            shutil.copystat(self.filename, new_filename)

        except Exception:
            LOGGER.exception('Problem while backing up file before save.')

        # TODO: make backups in .bibed_save/ ? (PREFERENCE ON/OFF)
        # TODO: clean old backup files. (PREFERENCE [number])
        pass

    def write(self):

        # assert lprint_function_name()
        # assert lprint(self.filename)

        filename = self.filename

        with self.files_store.no_watch(filename):

            if gpod('backup_before_save'):
                self.backup()

            with open(filename, 'w') as bibfile:
                bibfile.write(self.writer.write(self.bibdb))

        if __debug__:
            LOGGER.debug('{0}.write(): written to disk.'.format(self))

    def check_indexes(self):

        # assert lprint_function_name()

        for index, btp_entry in enumerate(self.bibdb.entries):

            # In rare cases (multiple deletion) the garbage collector does not
            # collect deleted keys fast enough. Thus we get() and handle the
            # situation gracefully.
            value = self.entries.get(btp_entry['ID'])

            try:
                current_value = value[1]

            except TypeError:
                continue

            if current_value != index:
                raise IndexingFailedError('{} is not {} (entry {})'.format(
                    self.entries[btp_entry['ID']][1],
                    index, btp_entry['ID']
                ))

        return True

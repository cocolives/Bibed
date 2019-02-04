
import os
import shutil
import datetime

import logging
import bibtexparser
from bibtexparser.bibdatabase import BibDatabase as BibtexParserDatabase

from bibed.exceptions import(
    BibedDatabaseException,
    BibedDatabaseError,
    IndexingFailedError,
)
from bibed.foundations import (  # NOQA
    BibedError,
    BibedException,
    lprint, ldebug,
    lprint_caller_name,
    lprint_function_name,
)
from bibed.preferences import gpod
from bibed.entry import BibedEntry


LOGGER = logging.getLogger(__name__)


# ———————————————————————————————————————————————————————— Controller Classes


class BibedDatabase:
    ''' Wraps a :mod:`bibtexparser` database, for faster access and
        higher-level operations between multiple databases, and synchronization
        with an underlying :class:`Gtk.ListStore`. '''

    def __init__(self, filename, store):
        ''' Create a :class:`~bibed.database.BibedDatabase` instance.

            :param filename: a full pathname, as a string, for a `BibTeX` /
                `BibLaTeX`
            :param store: a :class:`~bibed.store.BibedFileStore` instance. its
                `.data_store` attribute will be kept handy in the current
                database attributes.
        '''

        # TODO: think about getting rid of the whole bibtexparser level.
        #       it's using memory, for nothing more than what we do.
        #       We could at least remove the entries after load,
        #       and rebuild them just for write(), like we do for
        #       _internal_* fields at the BibedEntry level.

        self.filename    = filename
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

        assert self.bibdb.entries.index(entry.entry) == new_index

        self.data_store.insert_entry(entry)

    def delete_entry(self, entry):
        ''' Delete an entry from the current database.

            This operation will update underlying the Gtk datastore.

            .. note:: it's up to the caller to call :method:`write` on the
                database.
        '''
        # assert lprint_function_name()
        # assert lprint(entry, entry.gid)

        assert entry.gid >= 0

        entry_index = self.entries[entry.key][1]

        # Here, or at the end?
        self.data_store.delete_entry(entry)

        del self.entries[entry.key]

        self.bibdb.entries.pop(entry_index)

        # NOTE: 20190203: the underlying dict is updated correctly,
        # but only the first time you call it. It's a one shot.
        # lprint(self.bibdb.entries_dict.keys())

        # increment indexes of posterior entries
        for btp_entry in self.bibdb.entries[entry_index:]:
            self.entries[btp_entry['ID']][1] -= 1

        assert self.check_indexes()

    def move_entry(self, entry, destination_database):
        ''' Move an entry from a database to another.

            internally, this inserts the entry into the destination database,
            and then removes it from the source one. There could be some
            situations (application crash…) where the entry would be
            duplicated, or lost. Typically these situations have external
            causes.

            This operation will update underlying the Gtk datastore.

            .. note:: it's up to the caller to call :method:`write` on the
                two databases.

            :param entry: a :class:`~bibed.entry.BibedEntry` instance.
            :param destination_database: a :class:`bibed.database.BibedDatabase` instance.
        '''

        # assert lprint_function_name()

        assert entry.gid >= 0

        # This is important, else GUI will still write in source database.
        entry.database = destination_database

        # NOTE: this method does not update the data store, because
        #       add*() and delete*() methods already do what's needed.

        destination_database.add_entry(entry)

        self.delete_entry(entry)

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

    def check_indexes(self):

        # assert lprint_function_name()

        for index, btp_entry in enumerate(self.bibdb.entries):
            if self.entries[btp_entry['ID']][1] != index:
                raise IndexingFailedError('{} is not {} (entry {})'.format(
                    self.entries[btp_entry['ID']][1],
                    index, btp_entry['ID']
                ))

        return True

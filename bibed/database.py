
import os
import shutil
import datetime
import random
import functools

import logging
import bibtexparser
from bibtexparser.bibdatabase import BibDatabase as BibtexParserDatabase

from bibed.exceptions import DuplicateKeyError

from bibed.ltrace import (  # NOQA
    ldebug, lprint,
    lprint_caller_name,
    lprint_function_name,
)

from bibed.locale import _
from bibed.decorators import run_at_most_every
from bibed.constants import FileTypes
from bibed.strings import friendly_filename
from bibed.preferences import gpod
from bibed.entry import BibedEntry
from bibed.gtk import GObject

LOGGER = logging.getLogger(__name__)

bibtex_parser = functools.partial(
    bibtexparser.bparser.BibTexParser,
    ignore_nonstandard_types=False,
    interpolate_strings=False,
    common_strings=True,
)


def bibtex_writer():
    writer = bibtexparser.bwriter.BibTexWriter()
    writer.indent = '    '
    return writer


DATABASES_IDS = set()


def generate_database_id():

    new_id = random.randrange(131072)

    while new_id in DATABASES_IDS:
        new_id = random.randrange(131072)

    return new_id


# ———————————————————————————————————————————————————————— Controller Classes

class BibedDatabase(GObject.GObject):
    ''' GOject subclass that wraps a :mod:`bibtexparser` database for faster
        access, higher-level operations between multiple databases, and updates
        to a same-level :class:`Gtk.ListStore`.

        Beiing a GObject subclass makes it directly usable in GTK GUI objects,
        which is not the less cool feature of it.
    '''

    # NOTE: https://stackoverflow.com/a/11180599/654755

    objectid = GObject.property(type=int)
    filename = GObject.property(type=str)
    filetype = GObject.property(type=int, default=FileTypes.USER)

    # Used in the GUI to know which file(s) is(are) selected.
    selected = GObject.property(type=bool, default=False)

    files = None
    data = None

    @classmethod
    def move_entry(cls, entry, destination_database, write=True):
        ''' Move an entry from a database to another.

            internally, this inserts the entry into the destination database,
            and then removes it from the source one. There could be some
            situations (application crash…) where the entry would be
            duplicated, or lost. Typically these situations have external
            causes.

            This operation will update the underlying Gtk datastore.

            :param entry: a :class:`~bibed.entry.BibedEntry` instance.
            :param destination_database: a :class:`bibed.database.BibedDatabase` instance.
            :param save: boolean, which can be disabled in case of multiple
                move operations, for the caller to merge write() calls and
                optimize resources consumption.
        '''

        # assert lprint_function_name()

        assert entry.database is not None

        # This is important for the delete operation to act
        # on the right database, else “self” could be the
        # destination and thus delete() just after add().
        source_database = entry.database

        # NOTE: this method does not update the data store, because
        #       add*() and delete*() methods already do what's needed.

        source_database.delete_entry(entry)
        destination_database.add_entry(entry)

        if write:
            destination_database.write()
            source_database.write()

        LOGGER.debug('{0}.move_entry({1}) to {2} done (add+delete).'.format(
                     source_database, entry, destination_database))

    def __init__(self, filename, filetype):
        ''' Create a :class:`~bibed.database.BibedDatabase` instance.

            :param filename: a full pathname, as a string, for a `BibTeX` /
                `BibLaTeX` database.
            :param filetype: the application file type, from `FileTypes` enum. This is used in tooltips and other descriptive fields, to decide if full pathname or folder is shown or not.
        '''

        # TODO: think about getting rid of the whole bibtexparser level.
        #       it's using memory, for nothing more than what we do.
        #       We could at least remove the entries after load,
        #       and rebuild them just for write(), like we do for
        #       _internal_* fields at the BibedEntry level.

        super().__init__()

        self.objectid = generate_database_id()
        self.filename = filename
        self.filetype = filetype

        # TODO: detect BibTeX aliased fields and set
        #       self.use_aliased fields or convert them.

        try:
            with open(self.filename, 'r') as bibfile:
                bibdb = bibtex_parser().parse_file(bibfile)

        except IndexError:
            # empty file (probably just created)
            bibdb = BibtexParserDatabase()

        # Keep them for write.
        self.bibdb_attributes = {
            'comments': bibdb.comments,
            'preambles': bibdb.preambles,
            'strings': bibdb.strings,
        }

        self.entries = {}

        for btp_entry in bibdb.entries:

            key = btp_entry['ID']

            if key in self.entries:
                raise DuplicateKeyError(
                    _('Duplicate key {key} in {database}. You should '
                      'probably edit the file by hand to fix it.').format(
                        key=key, database=self.friendly_filename))

            self.entries[key] = BibedEntry(self, btp_entry)

        del bibdb

    def __str__(self):

        return 'BibedDatabase({}@{}{})'.format(
            self.friendly_filename,
            self.filetype,
            ' <selected>' if self.selected else '')

    def __len__(self):

        return len(self.entries)

    def __iter__(self):

        return iter(self.entries.values())

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

        return self.entries[key]

    def keys(self):

        assert lprint_function_name()

        return self.entries.keys()

    def itervalues(self):

        # assert lprint_function_name()

        for entry in self.entries.values():
            yield entry

    def values(self):

        # assert lprint_function_name()

        return self.entries.values()

    @property
    def friendly_filename(self):

        return friendly_filename(self.filename)

    # ———————————————————————————————————————————— databases/entries operations

    def add_entry(self, entry):
        ''' Add an entry into the current database.

            This operation will update the underlying Gtk datastore.

            .. note:: it's up to the caller to call :method:`write` on the
                database.
        '''

        # assert lprint_function_name()
        # assert lprint(entry)

        assert entry.key is not None
        assert entry.key not in self.entries

        # Make bi-directional link.
        entry.database = self
        self.entries[entry.key] = entry

        if BibedDatabase.data is not None:
            BibedDatabase.data.add_entry(entry)

        LOGGER.debug('{0}.add_entry({1}) done.'.format(self, entry))

    def delete_entry(self, entry, old_index=None):
        ''' Delete an entry from the current database.

            This operation will update the underlying Gtk datastore.

            .. note:: it's up to the caller to call :method:`write` on the
                database.
        '''
        # assert lprint_function_name()
        # assert lprint(entry, entry.gid)

        assert entry.key is not None
        assert entry.key in self.entries
        assert entry.database is not None
        assert entry.database == self

        if BibedDatabase.data is not None:
            BibedDatabase.data.delete_entry(entry)

        entry.database = None
        del self.entries[entry.key]

        # NOTE: do NOT delete the entry, in case it's a move operation.
        #       in case of a simple delete, the garbage collector should
        #       wipe it automatically anyway.

        LOGGER.debug('{0}.delete_entry({1}) done.'.format(self, entry))

    def update_entry_key(self, entry):

        # assert lprint_function_name()
        # assert lprint(entry)

        # delete and re-insert in BibedDatabase.
        for old_key in entry.ids:
            try:
                del self.entries[old_key]

            except KeyError:
                pass

        self.entries[entry.key] = entry

        entry.pivot_key()

        LOGGER.debug('{0}.update_entry_key({1}) done.'.format(self, entry))

    def backup(self):

        # assert lprint_function_name()
        # assert lprint(self.filename)

        dirname = os.path.dirname(self.filename)
        basename = os.path.basename(self.filename)
        coolname = friendly_filename(basename)

        # Using microseconds in backup filename should avoid collisions.
        # Using time will also help for cleaning old backups.
        new_filename = os.path.join(
            dirname,
            # HEADS UP: backup file starts with a dot, it's hidden.
            '.{coolname}.save.{datetime}.bib'.format(
                coolname=coolname,
                datetime=datetime.datetime.now().isoformat(sep='_')
            )
        )

        try:
            shutil.copyfile(self.filename, new_filename)
            shutil.copystat(self.filename, new_filename)

        except Exception:
            LOGGER.exception('Problem while backing up file before save.')

        backup_count = gpod('bib_backup_count')

        if backup_count is not None:

            backup_start = '.{basename}.save.'.format(basename=coolname)

            backup_files = []

            for root, dirs, files in os.walk(dirname):

                for walked_file in files:
                    if walked_file.startswith(backup_start):
                        backup_files.append(walked_file)

            if len(backup_files) > backup_count:

                for file_to_wipe in sorted(backup_files,
                                           reverse=True)[backup_count:]:
                    full_path = os.path.join(dirname, file_to_wipe)

                    os.unlink(full_path)

                    LOGGER.info(
                        '{0}.backup(): wiped old backup file “{1}”.'.format(
                            self, full_path))

        # TODO: make backups in .bibed_save/ ? (PREFERENCE ON/OFF)
        # TODO: clean old backup files. (PREFERENCE [number])
        LOGGER.debug('{0}.backup() done.'.format(self))

    def write(self, now=False):
        ''' Write the database to disk.

            :param now: should be ``True`` if you want to write now. Else,
                write calls will be combined, buffered and made at most every
                two seconds. In normal conditions, you should not touch the
                :param:`now` parameter. It is meant for inter-process
                synchronization.
        '''
        if now:
            return self.__database_write()

        else:
            return run_at_most_every(2000)(self.__database_write)

    def __database_write(self):

        assert lprint_function_name()
        assert lprint(self.filename)

        filename = self.filename

        with BibedDatabase.files.no_watch(filename):

            if gpod('backup_before_save'):
                self.backup()

            # Rebuild a BibtexParserDatabase
            # on the fly just for write.
            bibdb = BibtexParserDatabase()
            bibdb.comments = self.bibdb_attributes['comments']
            bibdb.preambles = self.bibdb_attributes['preambles']
            bibdb.strings = self.bibdb_attributes['strings']
            bibdb.entries = [
                self.entries[key].bib_dict
                for key
                in sorted(self.entries)
            ]

            with open(filename, 'w') as bibfile:
                bibfile.write(bibtex_writer().write(bibdb))

            del bibdb

        if __debug__:
            LOGGER.debug('{0}.write(): written to disk.'.format(self))

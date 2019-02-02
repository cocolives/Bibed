
import os
import shutil
import datetime

import logging
import bibtexparser
from bibtexparser.bibdatabase import BibDatabase as BibtexParserDatabase

from bibed.foundations import (  # NOQA
    lprint, ldebug,
    lprint_caller_name,
    lprint_function_name,
)
from bibed.preferences import gpod
from bibed.entry import BibedEntry


LOGGER = logging.getLogger(__name__)


class BibedDatabase:

    def __init__(self, filename, store):

        self.filename = filename
        self.store = store

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
            self.entries[entry['ID']] = (entry, index)

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

        # assert lprint_function_name()
        # assert lprint(entry)

        new_index = len(self.bibdb.entries)
        entry.index = new_index

        # Insert in BibedDatabase.
        self.entries[entry.key] = (entry.entry, new_index)

        # Idem in bibtexparser database.
        self.bibdb.entries.append(entry.entry)

    def update_entry_key(self, entry):

        # assert lprint_function_name()
        # assert lprint(entry)

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

        assert(entry.index)

    def backup(self):

        # assert lprint_function_name()
        # assert lprint(self.filename)

        dirname = os.path.dirname(self.filename)
        basename = os.path.basename(self.filename)

        # Using microseconds in backup filename should avoid collisions.
        # Using time will also help for cleaning old backups.
        new_filename = os.path.join(
            dirname,
            '{basename}.save.{datetime}.bib'.format(
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

        if gpod('backup_before_save'):
            self.backup()

        with open(self.filename, 'w') as bibfile:
                bibfile.write(self.writer.write(self.bibdb))

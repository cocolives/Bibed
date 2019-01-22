import logging
import bibtexparser

from bibed.preferences import defaults, preferences
from bibed.entry import BibedEntry


LOGGER = logging.getLogger(__name__)


class BibedDatabase:

    def __init__(self, filename):

        self.filename = filename

        self.parser = bibtexparser.bparser.BibTexParser(
            ignore_nonstandard_types=False,
            interpolate_strings=False,
            common_strings=True,
        )

        self.writer = bibtexparser.bwriter.BibTexWriter()
        self.writer.indent = '    '

        with open(self.filename, 'r') as bibfile:
            self.bibdb = self.parser.parse_file(bibfile)

        # self.bibdb.comments
        # self.bibdb.preambles
        # self.bibdb.strings

        self.entries = {}
        for index, entry in enumerate(self.bibdb.entries):
            self.entries[entry['ID']] = (entry, index)

    @property
    def make_backup(self):

        if preferences.make_backup is None:
            return defaults.make_backup

        return preferences.make_backup

    def get_entry_by_key(self, key):

        return BibedEntry(self, *self.entries[key])

    def values(self):

        for index, entry in enumerate(self.bibdb.entries):
            yield BibedEntry(self, entry, index)

    def save(self):

        # TODO: implement me.
        return

        if self.make_backup:
            # TODO: implement backup
            pass

        with open(self.filename, 'w') as bibfile:
                bibfile.write(self.writer.write(self.bibdb))

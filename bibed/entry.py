
import logging
import bibtexparser

from bibed.constants import (
    JABREF_QUALITY_KEYWORDS,
    JABREF_READ_KEYWORDS,
)

from bibed.preferences import defaults, preferences

LOGGER = logging.getLogger(__name__)


# ———————————————————————————————————————————————————————————————— Functions


bibtexparser_as_text = bibtexparser.bibdatabase.as_text


# —————————————————————————————————————————————————————————————————— Classes


class BibedEntry:

    @classmethod
    def new_from_type(cls, entry_type):

        LOGGER.info('New @{0} created'.format(entry_type))

        return cls(
            None,
            {'ENTRYTYPE': entry_type},
            -1,
        )

    @classmethod
    def single_bibkey_pattern_check(cls, pattern):

        if '@@key@@' in pattern:
            return pattern

        else:
            return defaults.accelerators.copy_to_clipboard_single_value

    @classmethod
    def single_bibkey_format(cls, bib_key):

        defls = defaults.accelerators.copy_to_clipboard_single_value
        prefs = preferences.accelerators.copy_to_clipboard_single_value

        if prefs is None:
            pattern = defls

        else:
            pattern = prefs

        pattern = cls.single_bibkey_pattern_check(pattern)

        result = pattern.replace('@@key@@', bib_key)

        return result

    def __init__(self, database, entry, index):
        self.entry = entry
        self.index = index
        self.database = database

    @property
    def type(self):
        return self.entry['ENTRYTYPE']

    @property
    def key(self):
        return self.entry.get('ID', None)

    @key.setter
    def key(self, value):

        # TODO: check key on the fly
        self.entry['ID'] = value

    def normalize(self, name):

        if name in ('ID', 'ENTRYTYPE', ):
            return name.upper()

        return name

    def get_field(self, name, default=None):

        name = self.normalize(name)

        if default is None:
            return bibtexparser_as_text(self.entry[name])

        return bibtexparser_as_text(self.entry.get(name, default))

    def set_field(self, name, value):

        name = self.normalize(name)

        self.entry[name] = value

    def __kw_split(self):
        return self.entry.get('keywords', '').split(',')

    @property
    def journal(self):
        return self.__clean_for_display('journal')

    @property
    def author(self):

        # TODO: handle {and}, "and", and other author particularities.

        return self.__clean_for_display('author')

    def __clean_for_display(self, name):

        # TODO: do better than this.

        field = bibtexparser_as_text(self.entry.get(name, ''))

        if field == '':
            return ''

        if field.startswith('{') and field.endswith('}'):
            field = field[1:-1]

        if '{' in field:
            field = field.replace('{', '').replace('}', '')

        field = field.replace('\\&', '&')

        return field

    @property
    def year(self):

        # TODO: handle non-ISO date gracefully.
        return int(
            self.entry.get('year',
                           self.entry.get('date', '0').split('-')[0])
        )

    @property
    def keywords(self):
        ''' Return entry keywords without JabRef internals. '''

        keywords = self.__kw_split()

        for kw in JABREF_QUALITY_KEYWORDS + JABREF_READ_KEYWORDS:
            try:
                keywords.remove(kw)
            except ValueError:
                pass

        return keywords

    @property
    def quality(self):
        ''' Get the JabRef quality from keywords. '''

        keywords = self.__kw_split()

        for kw in JABREF_QUALITY_KEYWORDS:
            if kw in keywords:
                return kw

        return ''

    @property
    def read_status(self):
        ''' Get the JabRef read status from keywords. '''

        keywords = self.__kw_split()

        for kw in JABREF_READ_KEYWORDS:
            if kw in keywords:
                return kw

        return ''

    def to_list_store_row(self):
        ''' Get a BIB entry, and get displayable fields for Gtk List Store. '''

        fields = self.entry

        return [
            0,  # global_id, computed by app.
            self.database.filename,
            self.index,
            self.type,
            self.key,
            fields.get('file', ''),
            fields.get('url', ''),
            fields.get('doi', ''),
            self.author,
            fields.get('title', ''),
            self.journal,
            self.year,
            fields.get('date', ''),
            self.quality,
            self.read_status,
        ]

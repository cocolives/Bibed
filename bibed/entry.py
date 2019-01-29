
import os
import logging
import datetime

import bibtexparser

from bibed.constants import (
    JABREF_QUALITY_KEYWORDS,
    JABREF_READ_KEYWORDS,
    ABSTRACT_MAX_LENGHT_IN_TOOLTIPS,
)

from bibed.preferences import defaults, preferences


LOGGER = logging.getLogger(__name__)


# ———————————————————————————————————————————————————————————————— Functions


bibtexparser_as_text = bibtexparser.bibdatabase.as_text


# —————————————————————————————————————————————————————————————————— Classes


class BibedEntry():

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

        # The raw bibtextparser entry.
        self.entry = entry

        # Our BibedDatabase.
        self.database = database

        # Index in the database file.
        # == index in the bibtexparser entries list.
        self.index = index

        # Global ID (across multiple files). This is
        # needed to update the treeview after modifications.
        self.gid = 0

        # Proxy keywords here for faster operations.
        self._internal_keywords = [
            x.strip()
            for x in self.entry.get('keywords', '').split(',')
            if x.strip() != ''
        ]

    def translate(self, name):
        ''' Translation Bibed ←→ bibtexparser. '''

        if name == 'key':
            return 'ID'

        # NO !!! we have type for thesis, etc.
        # elif name == 'type':
        #     return 'ENTRYTYPE'

        return name

    def fields(self):
        return self.entry.keys()

    def __setitem__(self, item_name, value):
        ''' Translation Bibed ←→ bibtexparser. '''

        self.entry[self.translate(item_name)] = value

    def __getitem__(self, item_name):

        return self.entry[self.translate(item_name)]

    def get_field(self, name, default=None):

        name = self.translate(name)

        if default is None:
            return bibtexparser_as_text(self.entry[name])

        return bibtexparser_as_text(self.entry.get(name, default))

    def set_field(self, name, value):

        name = self.translate(name)

        self.entry[name] = value

    @property
    def type(self):
        return self.entry['ENTRYTYPE']

    @type.setter
    def type(self, value):
        self.entry['ENTRYTYPE'] = value

    @property
    def key(self):
        return self.entry.get('ID', None)

    @key.setter
    def key(self, value):

        # TODO: check key validity on the fly ?
        #       this should be implemented higher
        #       in the GUI check_field*() methods.
        self.entry['ID'] = value

    @property
    def title(self):
        return self.entry.get('title', '')

    @property
    def comment(self):
        return self.entry.get('comment', '')

    @comment.setter
    def comment(self, value):

        self.entry['comment'] = value

    @property
    def tooltip(self):

        tooltips = []

        subtitle = self.get_field('subtitle', default='')

        base_tooltip = (
            '<big><i>{title}</i></big>\n{subtitle}'
            'by <b>{author}</b> ({year})'.format(
                title=self.title,
                subtitle='<i>{}</i>\n'.format(subtitle) if subtitle else '',
                author=self.author,
                year=self.year,
            )
        )

        if self.journal:
            base_tooltip += ', published in <b><i>{journal}</i></b>'.format(
                journal=self.journal)

        tooltips.append(base_tooltip)

        if self.comment:
            tooltips.append('<b>Comment:</b> {}'.format(self.comment))

        if self.keywords:
            tooltips.append('<b>Keywords:</b> {}'.format(
                ', '.join(self.keywords)))

        abstract = self.get_field('abstract', default='')

        if abstract:
            abstract = abstract[:ABSTRACT_MAX_LENGHT_IN_TOOLTIPS] \
                + (abstract[:ABSTRACT_MAX_LENGHT_IN_TOOLTIPS] and '[…]')

            tooltips.append('<b>Abstract</b>:\n{abstract}.'.format(
                abstract=abstract))

        timestamp = self.get_field('timestamp', default='')

        if timestamp:
            tooltips.append('Added to database <b>{timestamp}</b>.'.format(
                timestamp=timestamp))

        return '\n\n'.join(tooltips)

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

        # HEADS UP: copy(), else we alter _internal_keywords!
        keywords = self._internal_keywords[:]

        for kw in JABREF_QUALITY_KEYWORDS + JABREF_READ_KEYWORDS:
            try:
                keywords.remove(kw)
            except ValueError:
                pass

        return keywords

    @property
    def quality(self):
        ''' Get the JabRef quality from keywords. '''

        keywords = self._internal_keywords

        for kw in JABREF_QUALITY_KEYWORDS:
            if kw in keywords:
                return kw

        return ''

    @property
    def read_status(self):
        ''' Get the JabRef read status from keywords. '''

        keywords = self._internal_keywords

        for kw in JABREF_READ_KEYWORDS:
            if kw in keywords:
                return kw

        # NO keyword means book unread.
        # See constants.py
        return ''

    def add_keywords(self, keywords):

        self._internal_keywords.extend(keywords)

        self.entry['keywords'] = ', '.join(self._internal_keywords)

    def remove_keywords(self, keywords):

        for kw in keywords:
            try:
                self._internal_keywords.remove(kw)

            except IndexError:
                pass

        self.entry['keywords'] = ', '.join(self._internal_keywords)

    def toggle_quality(self):

        if self.quality == '':
            self.add_keywords([JABREF_QUALITY_KEYWORDS[0]])

        else:
            self.remove_keywords([JABREF_QUALITY_KEYWORDS[0]])

    def cycle_read_status(self):

        read_status = self.read_status

        if read_status == '':
            self.add_keywords([JABREF_READ_KEYWORDS[0]])

        elif read_status == JABREF_READ_KEYWORDS[0]:
            self.remove_keywords([JABREF_READ_KEYWORDS[0]])
            self.add_keywords([JABREF_READ_KEYWORDS[1]])

        else:
            self.remove_keywords([JABREF_READ_KEYWORDS[1]])

    def to_list_store_row(self):
        ''' Get a BIB entry, and get displayable fields for Gtk List Store. '''

        fields = self.entry

        return [
            self.gid,  # global_id, computed by app.
            self.database.filename,
            self.index,
            self.tooltip,
            self.type,
            self.key,
            fields.get('file', ''),
            fields.get('url', ''),
            fields.get('doi', ''),
            self.author,
            fields.get('title', ''),
            fields.get('subtitle', ''),
            self.journal,
            self.year,
            fields.get('date', ''),
            self.quality,
            self.read_status,
            self.comment,
        ]


class EntryFieldCheckMixin:
    ''' This class is meant to be subclassed by any Window/Dialog that checks entries.

        .. seealso:: :class:`~bibed.gui.BibedEntryDialog`.
    '''

    def check_field_year(self, field_name, field, field_value):

        field_value = field_value.strip()

        if len(field_value) != 4:
            return (
                'Invalid year.'
            )

        try:
            _ = int(field_value)

        except Exception as e:
            return (
                'Invalid year, not understood: {exc}.'.format(exc=e)
            )

    def check_field_key(self, field_name, field, field_value):

        # TODO: remove this test when auto-key-builder is implemented.
        if len(field_value.strip()) <= 3:
            return (
                'Key cannot be empty and must be at least 3 characters long.'
            )

        has_key = self.parent.application.check_has_key(field_value)

        if has_key:
            return (
                'Key already taken in <span '
                'face="monospace">{filename}</span>. '
                'Please choose another one.').format(
                    filename=os.path.basename(has_key)
            )

    def check_field_date(self, field_name, field, field_value):

        error_message = (
            'Invalid ISO date. '
            'Please type a date in the format YYYY-MM-DD.'
        )

        if len(field_value) < 10:
            return error_message

        try:
            _ = datetime.date.fromisoformat(field_value)

        except Exception as e:
            return '{error_message}\nExact error is: {exception}'.format(
                error_message=error_message, exception=e)

    check_field_urldate = check_field_date

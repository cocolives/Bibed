
import os
import re
import uuid
import logging
import datetime

import bibtexparser

from bibed.foundations import (
    lprint, ldebug,
    lprint_caller_name,
    lprint_function_name,
)

from bibed.constants import (
    FileTypes,
    JABREF_READ_KEYWORDS,
    JABREF_QUALITY_KEYWORDS,
    MAX_KEYWORDS_IN_TOOLTIPS,
    MINIMUM_BIB_KEY_LENGTH,
    ABSTRACT_MAX_LENGHT_IN_TOOLTIPS,
    COMMENT_LENGHT_FOR_CR_IN_TOOLTIPS,
)

from bibed.preferences import defaults, preferences, gpod
from bibed.utils import asciize
from bibed.exceptions import FileNotFoundError
from bibed.gui.helpers import markup_bib_filename
from bibed.gui.gtk import GLib


LOGGER = logging.getLogger(__name__)

# —————————————————————————————————————————————————————— regular expressions

KEY_RE = re.compile('^[a-z]([-:_a-z0-9]){2,}$', re.IGNORECASE)

# There is a non-breaking space and an space.
SPLIT_RE = re.compile(' | |:|,|;|\'|"|«|»|“|”|‘|’', re.IGNORECASE)

# ———————————————————————————————————————————————————————————————— Functions


bibtexparser_as_text = bibtexparser.bibdatabase.as_text


# —————————————————————————————————————————————————————————————————— Classes


class BibedEntry:
    '''

        Free fields from BibLaTeX documentation:

        - list[a–f]
        - user[a–f]
        - verb[a–c]

        Bibed uses `verbb` (for “verbatim-bibed”).
    '''

    VERBB_SEPARATOR    = '|'
    KEYWORDS_SEPARATOR = ','
    TRASHED_FROM       = 'trashedFrom'
    TRASHED_DATE       = 'trashedDate'

    @classmethod
    def new_from_type(cls, entry_type):

        LOGGER.info('New @{0} created'.format(entry_type))

        return cls(
            None,
            {'ENTRYTYPE': entry_type},
            # Index to -1 is checked in BibedEntryDialog
            # to ensure the new entry is written only once
            # into database.
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
        # TODO: remove this field, everywhere.
        self.index = index

        # Global ID (across multiple files). This is
        # needed to update the treeview after modifications.
        self.gid = 0

        self._internal_verbb = {
            key: value
            for (key, value) in (
                line.split(':')
                for line in self._internal_split_tokens(
                    self.entry.get('verbb', ''),
                    separator=self.VERBB_SEPARATOR
                )
            )
        }

        # Proxy keywords here for faster operations.
        self._internal_keywords = self._internal_split_tokens(
            self.entry.get('keywords', ''))

    def _internal_split_tokens(self, value, separator=None):

        if separator is None:
            separator = self.KEYWORDS_SEPARATOR

        return [
            expression.strip()
            for expression in value.split(separator)
            if expression.strip() != ''
        ]

    def _internal_add_keywords(self, keywords):

        self._internal_keywords.extend(keywords)

        self.entry['keywords'] = ', '.join(self._internal_keywords)

    def _internal_remove_keywords(self, keywords):

        for kw in keywords:
            try:
                self._internal_keywords.remove(kw)

            except IndexError:
                pass

        self.entry['keywords'] = ', '.join(self._internal_keywords)

    def _internal_translate(self, name):
        ''' Translation Bibed ←→ bibtexparser. '''

        if name == 'key':
            return 'ID'

        # NO !!! we have type for thesis, etc.
        # elif name == 'type':
        #     return 'ENTRYTYPE'

        return name

    def copy(self):
        ''' Return a copy of self, with no database and no index. '''

        return BibedEntry(None, self.entry.copy(), -1)

    def fields(self):
        return self.entry.keys()

    def __setitem__(self, item_name, value):
        ''' Translation Bibed ←→ bibtexparser. '''

        # TODO: keep this method or not ?
        #       we have more and more proxy specifics.
        #       Keeping this could lead to inconsistencies and bugs.

        value = value.strip()
        item_name = self._internal_translate(item_name)

        if value is None or value == '':
            try:
                del self.entry[item_name]
            except KeyError:
                # Situation: the field was initially empty. Then, in the
                # editor dialog, the field was filled, then emptied before
                # dialog close. Solution: don't crash.
                pass

            else:
                LOGGER.info('{0}: removing field {1} now empty.'.format(
                    self, item_name))

        else:
            self.entry[item_name] = value

    def __getitem__(self, item_name):

        # TODO: keep this method or not ?
        #       we have more and more proxy specifics.
        #       Keeping this could lead to inconsistencies and bugs.

        return self.entry[self._internal_translate(item_name)]

    def __str__(self):

        return 'Entry {}@{}'.format(self.key, self.type)

    def set_timestamp_and_owner(self):

        if gpod('bib_add_timestamp'):
            current_ts = self.entry.get('timestamp', None)

            if current_ts is None or gpod('bib_update_timestamp'):
                self.entry['timestamp'] = datetime.date.today().isoformat()

        owner_name = preferences.bib_owner_name

        if owner_name:
            owner_name = owner_name.strip()

            if gpod('bib_add_owner'):
                current_owner = self.entry.get('owner', None)

                if current_owner is None or gpod('bib_update_owner'):
                    self.entry['owner'] = owner_name

    def get_field(self, name, default=None):

        name = self._internal_translate(name)

        if default is None:
            return bibtexparser_as_text(self.entry[name])

        if name == 'keywords':
            return self.keywords

        return bibtexparser_as_text(self.entry.get(name, default))

    def set_field(self, name, value):

        name = self._internal_translate(name)

        try:
            setter = getattr(self, 'set_field_{}'.format(name))

        except AttributeError:
            self.entry[name] = value

        else:
            setter(value)

    def set_field_keywords(self, value):

        kw = self._internal_split_tokens(value)

        self._internal_keywords = kw + [self.read_status] + [self.quality]

        self.entry['keywords'] = ','.join(self._internal_keywords)

    @property
    def is_trashed(self):

        # assert lprint_function_name()

        return self.TRASHED_FROM in self._internal_verbb

    @property
    def trashed_informations(self):
        ''' Return trash-related information. '''

        # assert lprint_function_name()

        try:
            return (
                self._internal_verbb[self.TRASHED_FROM],
                self._internal_verbb[self.TRASHED_DATE],
            )
        except KeyError:
            return None

    def set_trashed(self, is_trashed=True):

        # assert lprint_function_name()
        # assert lprint(is_trashed)

        if is_trashed:
            assert not self.is_trashed

            self._internal_verbb[self.TRASHED_FROM] = self.database.filename
            self._internal_verbb[self.TRASHED_DATE] = datetime.date.today().isoformat()

        else:
            assert self.is_trashed

            del self._internal_verbb[self.TRASHED_FROM]
            del self._internal_verbb[self.TRASHED_DATE]

        self._internal_set_verbb()

    def _internal_set_verbb(self):
        ''' update `verbb` BibLaTeX field with our internal values. '''

        # assert lprint_function_name()

        self.entry['verbb'] = self.VERBB_SEPARATOR.join(
            ':'.join((key, value, ))
            for (key, value) in self._internal_verbb.items()
        )

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

        esc = self.escape_for_tooltip
        is_trashed = self.is_trashed

        def strike(text):
            return (
                '<s>{}</s>'.format(text)
                if is_trashed else text
            )

        tooltips = []

        subtitle = self.get_field('subtitle', default='')
        year     = self.year

        base_tooltip = (
            '<big><i>{title}</i></big>\n{subtitle}'
            'by <b>{author}</b>'.format(
                title=strike(esc(self.title)),
                subtitle='<i>{}</i>\n'.format(strike(esc(subtitle)))
                if subtitle else '',
                author=esc(self.author),
            )
        )

        if self.journal:
            base_tooltip += ', published in <b><i>{journal}</i></b>'.format(
                journal=esc(self.journal))

        if year:
            base_tooltip += ' ({year})'.format(year=year)

        tooltips.append(base_tooltip)

        if self.comment:
            tooltips.append('<b>Comment:</b>{cr}{comment}'.format(
                cr='\n'
                if len(self.comment) > COMMENT_LENGHT_FOR_CR_IN_TOOLTIPS
                else ' ',  # Note the space.
                comment=esc(self.comment)))

        abstract = self.get_field('abstract', default='')

        if abstract:
            abstract = abstract[:ABSTRACT_MAX_LENGHT_IN_TOOLTIPS] \
                + (abstract[ABSTRACT_MAX_LENGHT_IN_TOOLTIPS:] and '[…]')

            tooltips.append('<b>Abstract</b>:\n{abstract}'.format(
                abstract=esc(abstract)))

        keywords = self._internal_split_tokens(self.keywords)

        if keywords:
            if len(keywords) > MAX_KEYWORDS_IN_TOOLTIPS:
                kw_text = '{}{}'.format(
                    ', '.join(keywords[:MAX_KEYWORDS_IN_TOOLTIPS]),
                    ', and {} other(s).'.format(
                        len(keywords[MAX_KEYWORDS_IN_TOOLTIPS:])
                    ),
                )
            else:
                kw_text = ', '.join(keywords)

            tooltips.append('<b>Keywords:</b> {}'.format(kw_text))

        url = self.get_field('url', '')

        if url:
            tooltips.append('<b>URL:</b> <a href="{url}">{url}</a>'.format(url=url))

        if is_trashed:
            tFrom, tDate = self.trashed_informations

            missing = False

            try:
                tType = self.database.files_store.get_filetype(tFrom)

            except FileNotFoundError:
                # Most probably a deleted database, but could be also (99%)
                # that the current method is called while the origin BIB file
                # is unloaded. This happens notably at application start.

                if os.path.exists(tFrom):
                    tType = FileTypes.USER

                else:
                    tType = FileTypes.NOTFOUND
                    missing = True

            # TODO: what if trashed from QUEUE? FileTypes must be dynamic!
            tFrom = markup_bib_filename(
                tFrom, tType, parenthesis=True, missing=missing)

            tooltips.append('Trashed from {tFrom} on {tDate}.'.format(
                tFrom=tFrom, tDate=tDate))

        else:
            timestamp = self.get_field('timestamp', default='')

            if timestamp:
                tooltips.append('Added to {filename} on <b>{timestamp}</b>.'.format(
                    filename=markup_bib_filename(
                        self.database.filename,
                        self.database.filetype),
                    timestamp=timestamp))

            else:
                tooltips.append('Stored in {filename}.'.format(
                    filename=markup_bib_filename(
                        self.database.filename,
                        self.database.filetype,
                        parenthesis=True)))

        return '\n\n'.join(tooltips)

    @property
    def journal(self):

        # TODO: use journaltitle / handle aliased fields.

        for field_name in ('journaltitle', 'booktitle', 'journal'):
            field_value = self.__clean_for_display(field_name)

            if field_value:
                return field_value

        return ''

    @property
    def author(self):

        # TODO: handle {and}, "and", and other author particularities.

        return self.__clean_for_display('author')

    def escape_for_tooltip(self, text):
        ''' Escape esperluette and other entities for GTK tooltip display. '''

        # .replace('& ', '&amp; ')

        text = GLib.markup_escape_text(text)

        # TODO: re.sub() sur texttt, emph, url, etc.
        #       probably some sort of TeX → Gtk Markup.
        #       and code the opposite for rich text
        #       editor on abstract / comment.

        return text

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
        ''' Will try to return year field or year part of date field. '''

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

        return ', '.join(keywords)

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

    @property
    def short_display(self):
        ''' Used in GUI dialogs (thus uses Pango markup). '''

        assert getattr(defaults.types.labels, self.type)

        if self.is_trashed:
            trashedFrom, trashedDate = self.trashed_informations
        else:
            trashedFrom, trashedDate = None, None

        return (
            '{type} <b><i>{title}</i></b> '
            'by <b>{author}</b>{journal}{year}{trashed}'.format(
                type=getattr(defaults.types.labels,
                             self.type).replace('_', ''),

                title=self.title[:24] + (self.title[24:] and ' […]'),
                author=self.author,

                journal=' in <i>{}</i>'.format(self.journal)
                if self.journal else '',

                year=' ({})'.format(self.year)
                if self.year else '',

                trashed=' <span color="grey">(trashed on {tDate} from <span face="monospace">{tFrom}</span>)</span>'.format(
                    tFrom=GLib.markup_escape_text(
                        os.path.basename(trashedFrom)),
                    tDate=trashedDate
                ) if self.is_trashed else '',
            )
        )

    def update_fields(self, **kwargs):

        # assert lprint_function_name()
        # assert lprint(kwargs)

        for field_name, field_value in kwargs.items():
            self[field_name] = field_value

        self.set_timestamp_and_owner()

    def toggle_quality(self):

        if self.quality == '':
            self._internal_add_keywords([JABREF_QUALITY_KEYWORDS[0]])

        else:
            self._internal_remove_keywords([JABREF_QUALITY_KEYWORDS[0]])

        self.set_timestamp_and_owner()

    def cycle_read_status(self):

        read_status = self.read_status

        if read_status == '':
            self._internal_add_keywords([JABREF_READ_KEYWORDS[0]])

        elif read_status == JABREF_READ_KEYWORDS[0]:
            self._internal_remove_keywords([JABREF_READ_KEYWORDS[0]])
            self._internal_add_keywords([JABREF_READ_KEYWORDS[1]])

        else:
            self._internal_remove_keywords([JABREF_READ_KEYWORDS[1]])

        self.set_timestamp_and_owner()

    def delete(self, write=True):

        self.database.delete_entry(self)

        if write:
            self.database.write()


class EntryKeyGenerator:

    @staticmethod
    def format_title(title):
        ''' Return first letter of each word. '''

        words = (word.strip() for word in SPLIT_RE.split(title))

        return asciize(''.join(
            word[0] for word in words if word
        ), aggressive=True).lower()

    @staticmethod
    def format_author(author):

        def get_last_name(name):

            try:
                return name.rsplit(' ', 1)[1]

            except IndexError:
                # No space, no split, only one name part.
                return name

        names = [name.strip() for name in author.split('and')]

        names_count = len(names)

        if names_count > 2:
            last_names = (get_last_name(name) for name in names)

            # Take the 2 first letters of each author last name.
            last_name = ''.join(
                asciize(name[:2], aggressive=True) for name in last_names)

        elif names_count == 2:

            last_names = (get_last_name(name) for name in names)

            # Take the 3 first letters of each author last name.
            last_name = ''.join(
                asciize(name[:3], aggressive=True) for name in last_names)

        else:
            last_name = asciize(get_last_name(names[0]), aggressive=True)

        return last_name.lower()

    @staticmethod
    def generate_new_key(entry, suffix=None):

        assert isinstance(entry, BibedEntry)

        assert suffix is None or int(suffix)

        if suffix is None:
            suffix = ''

        else:
            # return someting like '-03'
            suffix = '-{:02d}'.format(suffix)

        author = entry.author
        title = entry.title
        year = entry.year

        if entry.type not in (
                'book', 'article', 'misc', 'booklet', 'thesis', 'online'):
            prefix = '{}:'.format(entry.type[0].lower())

        else:
            prefix = ''

        if not author and not title:
            # Nothing to make a key from…
            return uuid.uuid4().hex

        if not title:
            result = '{prefix}{author}{year}{suffix}'.format(
                prefix=prefix, author=EntryKeyGenerator.format_author(author),
                year=year, suffix=suffix)

        elif not author:
            result = '{prefix}{title}{year}{suffix}'.format(
                prefix=prefix, title=EntryKeyGenerator.format_title(title),
                year=year, suffix=suffix)

        else:
            # We've got an author and a title
            result = '{prefix}{author}-{title}{suffix}'.format(
                prefix=prefix, author=EntryKeyGenerator.format_author(author),
                title=EntryKeyGenerator.format_title(title), suffix=suffix)

        result_len = len(result)

        if result_len < MINIMUM_BIB_KEY_LENGTH:
            result = '{result}{padding}'.format(
                result=result,
                padding=uuid.uuid4().hex[:MINIMUM_BIB_KEY_LENGTH - result_len]
            )

        return result


generate_new_key = EntryKeyGenerator.generate_new_key


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

        field_value = field_value.strip()

        if KEY_RE.match(field_value) is None:
            return (
                'Key must start with a letter, contain only letters and numbers; special characters allowed: “-”, “:” and “_”.'
            )

        has_key = self.files.has_bib_key(field_value)

        if has_key:
            return (
                'Key already taken in <span '
                'face="monospace">{filename}</span>. '
                'Please choose another one.').format(
                    filename=os.path.basename(has_key)
            )

    def fix_field_key(self, field_name, field, field_value, entry, files):
        ''' Create a valid key. '''

        assert entry
        assert files

        new_key = generate_new_key(entry)
        counter = 1

        while files.has_bib_key(new_key):

            new_key = generate_new_key(entry, counter)
            counter += 1

        return new_key

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

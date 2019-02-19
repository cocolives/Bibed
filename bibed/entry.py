
import os
import re
import uuid
import logging
import datetime

import bibtexparser

from bibed.ltrace import (
    lprint, ldebug,
    lprint_caller_name,
    lprint_function_name,
)

from bibed.constants import (
    BibAttrs, FileTypes,
    JABREF_READ_KEYWORDS,
    JABREF_QUALITY_KEYWORDS,
    MAX_KEYWORDS_IN_TOOLTIPS,
    MINIMUM_BIB_KEY_LENGTH,
    ABSTRACT_MAX_LENGHT_IN_TOOLTIPS,
    COMMENT_LENGHT_FOR_CR_IN_TOOLTIPS,
)

from bibed.strings import asciize
from bibed.locale import _
from bibed.fields import FieldUtils as fu
from bibed.preferences import defaults, preferences, gpod
from bibed.exceptions import FileNotFoundError
from bibed.gui.helpers import markup_bib_filename
from bibed.gtk import GLib


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

    files_store = None

    @classmethod
    def new_from_type(cls, entry_type):

        LOGGER.info('New @{0} created'.format(entry_type))

        return cls(
            None,
            {'ENTRYTYPE': entry_type},
        )

    @classmethod
    def new_from_entry(cls, entry_to_dupe):

        new_entry = cls(
            entry_to_dupe.database,
            entry_to_dupe.entry.copy(),
        )

        # It's a new entry. Wipe key, else the old could get overwritten.
        del new_entry.entry['ID']

        LOGGER.info('Entry {0} duplicated into {1}'.format(
            entry_to_dupe, new_entry))

        return new_entry

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

    # ———————————————————————————————————————————— Python / dict-like behaviour

    def __init__(self, database, entry):

        # The raw bibtextparser entry.
        self.bib_dict = entry

        # Our BibedDatabase.
        self.database = database

        self.__internal_verbb = {
            key: value
            for (key, value) in (
                line.split(':')
                for line in self.__internal_split_tokens(
                    self.bib_dict.get('verbb', ''),
                    separator=self.VERBB_SEPARATOR
                )
            )
        }

        # Proxy keywords here for faster operations.
        self.__internal_keywords = self.__internal_split_tokens(
            self.bib_dict.get('keywords', ''))

    def __setitem__(self, item_name, value):
        ''' Translation Bibed ←→ bibtexparser. '''

        # TODO: keep this method or not ?
        #       we have more and more proxy specifics.
        #       Keeping this could lead to inconsistencies and bugs.

        value = value.strip()
        item_name = self.__internal_translate(item_name)

        if value is None or value == '':
            try:
                del self.bib_dict[item_name]
            except KeyError:
                # Situation: the field was initially empty. Then, in the
                # editor dialog, the field was filled, then emptied before
                # dialog close. Solution: don't crash.
                pass

            else:
                LOGGER.info('{0}: removing field {1} now empty.'.format(
                    self, item_name))

        else:
            self.bib_dict[item_name] = value

    def __getitem__(self, item_name):

        # TODO: keep this method or not ?
        #       we have more and more proxy specifics.
        #       Keeping this could lead to inconsistencies and bugs.

        return self.bib_dict[self.__internal_translate(item_name)]

    def __str__(self):

        return 'Entry {}@{}{}'.format(
            self.key, self.type,
            ' NEW' if self.database is None
            else ' in {}'.format(
                self.database))

    def copy(self):
        ''' Return a copy of self, with no database and. '''

        return BibedEntry(None, self.bib_dict.copy())

    # ——————————————————————————————————————————————————————————————— Internals

    def __internal_split_tokens(self, value, separator=None):

        if separator is None:
            separator = self.KEYWORDS_SEPARATOR

        return [
            expression.strip()
            for expression in value.split(separator)
            if expression.strip() != ''
        ]

    def __internal_add_keywords(self, keywords):

        self.__internal_keywords.extend(keywords)

        self.bib_dict['keywords'] = ', '.join(self.__internal_keywords)

    def __internal_remove_keywords(self, keywords):

        for kw in keywords:
            try:
                self.__internal_keywords.remove(kw)

            except IndexError:
                pass

        self.bib_dict['keywords'] = ', '.join(self.__internal_keywords)

    def __internal_translate(self, name):
        ''' Translation Bibed ←→ bibtexparser. '''

        if name == 'key':
            return 'ID'

        # Do not translate `type`.
        # We have a `type` field for thesis, etc.
        # elif name == 'type':
        #     return 'ENTRYTYPE'

        return name

    def __internal_set_verbb(self):
        ''' update `verbb` BibLaTeX field with our internal values. '''

        # assert lprint_function_name()

        self.bib_dict['verbb'] = self.VERBB_SEPARATOR.join(
            ':'.join((key, value, ))
            for (key, value) in self.__internal_verbb.items()
        )

    def __escape_for_tooltip(self, text):
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

        field = bibtexparser_as_text(self.bib_dict.get(name, ''))

        if field == '':
            return ''

        if field.startswith('{') and field.endswith('}'):
            field = field[1:-1]

        if '{' in field:
            field = field.replace('{', '').replace('}', '')

        field = field.replace('\\&', '&')

        return field

    # ———————————————————————————————————————————————————— Methods & attributes

    def fields(self):

        return self.bib_dict.keys()

    def set_timestamp_and_owner(self):

        if gpod('bib_add_timestamp'):
            current_ts = self.bib_dict.get('timestamp', None)

            if current_ts is None or gpod('bib_update_timestamp'):
                self.bib_dict['timestamp'] = datetime.date.today().isoformat()

        owner_name = preferences.bib_owner_name

        if owner_name:
            owner_name = owner_name.strip()

            if gpod('bib_add_owner'):
                current_owner = self.bib_dict.get('owner', None)

                if current_owner is None or gpod('bib_update_owner'):
                    self.bib_dict['owner'] = owner_name

    def get_field(self, name, default=None):
        ''' Used massively and exclusively in editor dialog and data store. '''

        # We should use properties for these attributes.
        if name == 'keywords':
            return ', '.join(self.keywords)

        name = self.__internal_translate(name)

        if default is None:
            return bibtexparser_as_text(self.bib_dict[name])

        return bibtexparser_as_text(self.bib_dict.get(name, default))

    def set_field(self, name, value):

        if value in (None, '', ):
            # remove field. Doing this here is
            # required by field mechanics in GUI.
            del self.bib_dict[name]
            return

        name = self.__internal_translate(name)

        try:
            setter = getattr(self, 'set_field_{}'.format(name))

        except AttributeError:
            self.bib_dict[name] = value

        else:
            setter(value)

    def set_field_keywords(self, value):

        kw = self.__internal_split_tokens(value)

        self.__internal_keywords = kw + [self.read_status] + [self.quality]

        # Flatten for bibtexparser
        final_keywords = ','.join(
            # If no read_status or quality, we need to “re-cleanup”
            kw for kw in self.__internal_keywords if kw.strip() != ''
        )

        if final_keywords != '':
            self.bib_dict['keywords'] = final_keywords

        else:
            # remove now-empty field.
            del self.bib_dict['keywords']

    # —————————————————————————————————————————————————————————————— properties

    @property
    def is_trashed(self):

        # assert lprint_function_name()

        return self.TRASHED_FROM in self.__internal_verbb

    @property
    def trashed_informations(self):
        ''' Return trash-related information. '''

        # assert lprint_function_name()

        try:
            return (
                self.__internal_verbb[self.TRASHED_FROM],
                self.__internal_verbb[self.TRASHED_DATE],
            )
        except KeyError:
            return None

    def set_trashed(self, is_trashed=True):

        # assert lprint_function_name()
        # assert lprint(is_trashed)

        if is_trashed:
            assert not self.is_trashed

            self.__internal_verbb[self.TRASHED_FROM] = self.database.filename
            self.__internal_verbb[self.TRASHED_DATE] = \
                datetime.date.today().isoformat()

        else:
            assert self.is_trashed

            del self.__internal_verbb[self.TRASHED_FROM]
            del self.__internal_verbb[self.TRASHED_DATE]

        self.__internal_set_verbb()

    @property
    def type(self):

        return self.bib_dict['ENTRYTYPE']

    @type.setter
    def type(self, value):

        self.bib_dict['ENTRYTYPE'] = value

    @property
    def key(self):

        return self.bib_dict.get('ID', None)

    @key.setter
    def key(self, value):

        # TODO: check key validity on the fly ?
        #       this should be implemented higher
        #       in the GUI check_field*() methods.
        self.bib_dict['ID'] = value

    @property
    def title(self):

        return self.bib_dict.get('title', '')

    @property
    def comment(self):

        return self.bib_dict.get('comment', '')

    @comment.setter
    def comment(self, value):

        self.bib_dict['comment'] = value

    @property
    def tooltip(self):

        esc = self.__escape_for_tooltip
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

        keywords = self.keywords

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
                tType = BibedEntry.files_store.get_filetype(tFrom)

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
    def col_in_or_by(self):

        if self.bib_dict['ENTRYTYPE'] == 'article':
            fields_names = (
                'journaltitle', 'booktitle',
                # backward compatible field name for JabRef.
                'journal',
            )

        elif 'book' in self.bib_dict['ENTRYTYPE']:
            fields_names = (
                'publisher',
                'booktitle',
                'isbn',
            )

        else:
            fields_names = (
                'howpublished',
                'institution',
                'school',
                'organization',
            )

        for field_name in fields_names:

            if isinstance(field_name, tuple):
                values = []

                for subfield_name in field_name:
                    field_value = self.__clean_for_display(subfield_name)

                    if field_value:
                        if subfield_name == 'edition':
                            values.append(
                                '<span color="grey">{}</span>'.format(
                                    format_edition(field_value, short=True)))

                        else:
                            values.append(markup_escape_text(field_value))

                if values:
                    return ', '.join(values)

            else:
                field_value = self.__clean_for_display(field_name)

                if field_value:
                    return markup_escape_text(field_value)

        return ''

    @property
    def author(self):

        # TODO: handle {and}, "and", and other author particularities.

        return self.__clean_for_display('author')

    @property
    def year(self):
        ''' Will try to return year field or year part of date field. '''

        # TODO: handle non-ISO date gracefully.
        return int(
            self.bib_dict.get(
                'year',
                self.bib_dict.get('date', '0').split('-')[0])
        )

    @property
    def keywords(self):
        ''' Return entry keywords without JabRef internals. '''

        # HEADS UP: copy(), else we alter __internal_keywords!
        keywords = self.__internal_keywords[:]

        for kw in JABREF_QUALITY_KEYWORDS + JABREF_READ_KEYWORDS:
            try:
                keywords.remove(kw)

            except ValueError:
                pass

        return keywords

    @property
    def quality(self):
        ''' Get the JabRef quality from keywords. '''

        keywords = self.__internal_keywords

        for kw in JABREF_QUALITY_KEYWORDS:
            if kw in keywords:
                return kw

        return ''

    @property
    def read_status(self):
        ''' Get the JabRef read status from keywords. '''

        keywords = self.__internal_keywords

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

                in_or_by=' in <i>{}</i>'.format(self.col_in_or_by)
                if self.col_in_or_by else '',

                year=' ({})'.format(self.year)
                if self.year else '',

                trashed=' <span color="grey">(trashed on {tDate} from <span face="monospace">{tFrom}</span>)</span>'.format(
                    tFrom=GLib.markup_escape_text(
                        os.path.basename(trashedFrom)),
                    tDate=trashedDate
                ) if self.is_trashed else '',
            )
        )

    # ————————————————————————————————————————————————————————————————— Methods

    def update_fields(self, **kwargs):

        # assert lprint_function_name()
        # assert lprint(kwargs)

        update_store = kwargs.pop('update_store', True)

        LOGGER.debug('{0}.update_fields({1})'.format(self, kwargs))

        for field_name, field_value in kwargs.items():
            # Use set_field() to automatically handle special cases.
            self.set_field(field_name, field_value)

        self.set_timestamp_and_owner()

        if update_store:
            # TODO: map entry fields to data_store fields?
            #       for now it's not worth it.
            self.update_store_row()

    def update_store_row(self, fields=None):

        if self.database:
            LOGGER.debug('{0}.update_store_row({1})'.format(self, fields))
            # If we have no database, entry is not yet created.
            # The data store will be updated later by add_entry().
            self.database.data_store.update_entry(self, fields)

    def toggle_quality(self):

        if self.quality == '':
            self.__internal_add_keywords([JABREF_QUALITY_KEYWORDS[0]])

        else:
            self.__internal_remove_keywords([JABREF_QUALITY_KEYWORDS[0]])

        self.set_timestamp_and_owner()

        self.update_store_row({BibAttrs.QUALITY: self.quality})

    def cycle_read_status(self):

        read_status = self.read_status

        if read_status == '':
            self.__internal_add_keywords([JABREF_READ_KEYWORDS[0]])

        elif read_status == JABREF_READ_KEYWORDS[0]:
            self.__internal_remove_keywords([JABREF_READ_KEYWORDS[0]])
            self.__internal_add_keywords([JABREF_READ_KEYWORDS[1]])

        else:
            self.__internal_remove_keywords([JABREF_READ_KEYWORDS[1]])

        self.set_timestamp_and_owner()

        self.update_store_row({BibAttrs.READ: self.read_status})

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

    # ——————————————————————————————————————————————————————————— Check methods

    def check_field_year(self, all_fields, field_name, field, field_value):

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

    def check_field_key(self, all_fields, field_name, field, field_value):

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

    def check_field_date(self, all_fields, field_name, field, field_value):

        error_message = (
            'Invalid ISO date. '
            'Please type a date in the format YYYY-MM-DD.'
        )

        if fu.value_is_empty(field_value):
            # User has removed the date after having
            # typed something. Everything is fine.
            return

        if len(field_value) < 10:
            return error_message

        try:
            _ = datetime.date.fromisoformat(field_value)

        except Exception as e:
            return '{error_message}\nExact error is: {exception}'.format(
                error_message=error_message, exception=e)

    check_field_urldate = check_field_date

    def check_field_url(self, all_fields, field_name, field, field_value):

        if fu.value_is_empty(field_value):
            # The URL was made empty after beiing set. Empty the date.
            fu.field_make_empty(all_fields['urldate'])
            return

        fu.field_set_date_today(all_fields['urldate'])

    # ————————————————————————————————————————————————————————————— Fix methods

    def fix_field_key(self, all_fields, field_name, field, field_value, entry, files):
        ''' Create a valid key. '''

        assert entry
        assert files

        new_key = generate_new_key(entry)
        counter = 1

        while files.has_bib_key(new_key):

            new_key = generate_new_key(entry, counter)
            counter += 1

        return new_key

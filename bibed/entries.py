
from bibed.constants import (
    JABREF_READ_KEYWORDS,
    JABREF_QUALITY_KEYWORDS,
)

from bibed.preferences import defaults, preferences


def entry_get_keywords(entry):
    ''' Return entry keywords without JabRef internals. '''

    keywords = entry.fields.get('keywords', [])

    for kw in JABREF_QUALITY_KEYWORDS + JABREF_READ_KEYWORDS:
        try:
            keywords.remove(kw)
        except ValueError:
            pass

    return keywords


def entry_get_quality(entry):
    ''' Get the JabRef quality from keywords. '''

    keywords = entry.fields.get('keywords', '').split(',')

    for kw in JABREF_QUALITY_KEYWORDS:
        if kw in keywords:
            return kw

    return ''


def entry_get_read_status(entry):
    ''' Get the JabRef read status from keywords. '''

    keywords = entry.fields.get('keywords', '').split(',')

    for kw in JABREF_READ_KEYWORDS:
        if kw in keywords:
            return kw

    return ''


def bib_entry_format_author_pybtex(persons):

    if persons is None:
        return '—'

    pstring = ''
    local_pstring = ''

    for p in persons:
        local_pstring = '{0} {1} {2} {3}'.format(
            p.first_names[0] if p.first_names else '',
            p.middle_names[0] if p.middle_names else '',
            p.prelast_names[0] if p.prelast_names else '',
            p.last_names[0] if p.last_names else '')

        local_pstring = local_pstring.strip()

        if local_pstring.startswith('{'):
            local_pstring = local_pstring[1:-1]

        pstring += local_pstring + ', '

    while '  ' in pstring:
        pstring = pstring.replace('  ', ' ')

    if pstring.endswith(', '):
        pstring = pstring[:-2]

    return pstring


def bib_entry_format_journal_pybtex(journal):

    if journal == '':
        return ''

    if journal.startswith('{'):
        journal = journal[1:-1]

    journal = journal.replace('\\&', '&')

    return journal


bib_entry_format_author = bib_entry_format_author_pybtex
bib_entry_format_journal = bib_entry_format_journal_pybtex


def bib_entry_to_store_row_list_pybtex(global_counter, origin, counter, entry):
    ''' Get a BIB entry, and get displayable fields for Gtk List Store. '''

    fields = entry.fields
    persons = entry.persons

    return [
        global_counter,
        origin,
        counter,
        entry.type,
        entry.key,
        fields.get('file', ''),
        fields.get('url', ''),
        fields.get('doi', ''),
        bib_entry_format_author(persons.get('author', None)),
        fields.get('title', ''),
        bib_entry_format_journal(fields.get('journal', '')),
        int(fields.get('year', fields.get('date', '0').split('-')[0])),
        fields.get('date', ''),
        entry_get_quality(entry),
        entry_get_read_status(entry),
    ]


bib_entry_to_store_row_list = bib_entry_to_store_row_list_pybtex


def single_bibkey_to_copy_check(pattern):

    if '@@key@@' in pattern:
        return pattern

    else:
        return defaults.accelerators.copy_to_clipboard_single_value


def format_single_bibkey_to_copy(bib_key):

    defls = defaults.accelerators.copy_to_clipboard_single_value
    prefs = preferences.accelerators.copy_to_clipboard_single_value

    if prefs is None:
        pattern = defls

    else:
        pattern = prefs

    pattern = single_bibkey_to_copy_check(pattern)

    result = pattern.replace('@@key@@', bib_key)

    return result

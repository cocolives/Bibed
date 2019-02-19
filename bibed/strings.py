
import os
import re
from datetime import timedelta

from bibed.exceptions import BibedStringException
from bibed.gtk import GLib

def utf8_normalise_translation_map(translation_map):

    return tuple(
        (GLib.utf8_normalize(to_trans, -1, GLib.NormalizeMode.DEFAULT), to_what, )
        for to_trans, to_what in translation_map
    )


TRANSLATION_MAP_LOWER = (
    # lower-case
    ('á', 'a'), ('à', 'a'), ('â', 'a'), ('ä', 'a'),
    ('ã', 'a'), ('å', 'a'), ('ă', 'a'), ('ā', 'a'), ('æ', 'ae'),
    ('ç', 'c'),
    ('é', 'e'), ('è', 'e'), ('ê', 'e'), ('ë', 'e'), ('ẽ', 'e'),
    ('í', 'i'), ('ì', 'i'), ('î', 'i'), ('ï', 'i'), ('ĩ', 'i'),
    ('ñ', 'n'),
    ('ó', 'o'), ('ò', 'o'), ('ô', 'o'), ('ö', 'o'),
    ('õ', 'o'), ('ø', 'o'), ('œ', 'oe'),
    ('ú', 'u'), ('ù', 'u'), ('û', 'u'), ('ü', 'u'), ('ũ', 'u'),
    ('ý', 'y'), ('ỳ', 'y'), ('ŷ', 'y'), ('ÿ', 'y'), ('ỹ', 'y'),
)

TRANSLATION_MAP_UPPER = (
    # Upper-case
    ('Á', 'A'), ('À', 'A'), ('Â', 'A'), ('Ä', 'A'),
    ('Ã', 'A'), ('Å', 'A'), ('Ă', 'A'), ('Ā', 'A'), ('Æ', 'AE'),
    ('Ç', 'C'),
    ('É', 'E'), ('È', 'E'), ('Ê', 'E'), ('Ë', 'E'), ('Ẽ', 'E'),
    ('Í', 'I'), ('Ì', 'i'), ('Î', 'i'), ('Ï', 'i'), ('Ĩ', 'i'),
    ('Ñ', 'N'),
    ('Ó', 'O'), ('Ò', 'O'), ('Ô', 'O'), ('Ö', 'O'),
    ('Õ', 'O'), ('Ø', 'O'), ('Œ', 'OE'),
    ('Ú', 'U'), ('Ù', 'U'), ('Û', 'U'), ('Ü', 'U'), ('Ũ', 'U'),
    ('Ý', 'Y'), ('Ỳ', 'Y'), ('Ŷ', 'Y'), ('Ÿ', 'Y'), ('Ỹ', 'Y'),
)

TRANSLATION_MAP_EXTENDED = (
    # no-special-case chars
    ('ß', 'ss'), ('þ', ''), ('ð', ''), ('µ', ''), ('$', ''),
    ('€', ''), ('§', ''), ('~', ''), ('&', ''), ('/', ''), ('=', ''),
)

TRANSLATION_MAP_TYPOGRAPHIC = (
    # typographic chars
    ("'", ''), ('"', ''), ('«', ''), ('»', ''),
    ('“', ''), ('”', ''), ('‘', ''), ('’', ''),

    # Things that can be in BibLaTeX strings.
    ('(', ''), (')', ''), ('[', ''), (']', ''), ('{', ''), ('}', ''),
    ('\\', ''), ('`', ''), ('^', ''), ('%', ''), ('*', ''), ('@', ''),

    # standard space and non-breaking
    (' ', '_'), (' ', '_'),

    # Other special
    ('©', ''), ('®', ''),
)


TRANSLATION_MAP_FULL = (
    TRANSLATION_MAP_LOWER
    + TRANSLATION_MAP_UPPER
    + TRANSLATION_MAP_EXTENDED
    + TRANSLATION_MAP_TYPOGRAPHIC
)

# The UTF8 normalized versions are because of
# https://lazka.github.io/pgi-docs/GLib-2.0/functions.html#GLib.utf8_normalize
# https://lazka.github.io/pgi-docs/Gtk-3.0/callbacks.html#Gtk.EntryCompletionMatchFunc

TRANSLATION_MAP_LOWER_UTF8_NORM = \
    utf8_normalise_translation_map(TRANSLATION_MAP_LOWER)

TRANSLATION_MAP_UPPER_UTF8_NORM = \
    utf8_normalise_translation_map(TRANSLATION_MAP_UPPER)

TRANSLATION_MAP_EXTENDED_UTF8_NORM = \
    utf8_normalise_translation_map(TRANSLATION_MAP_EXTENDED)

TRANSLATION_MAP_TYPOGRAPHIC_UTF8_NORM = \
    utf8_normalise_translation_map(TRANSLATION_MAP_TYPOGRAPHIC)

TRANSLATION_MAP_FULL_UTF8_NORM = (
    TRANSLATION_MAP_LOWER_UTF8_NORM
    + TRANSLATION_MAP_UPPER_UTF8_NORM
    + TRANSLATION_MAP_EXTENDED_UTF8_NORM
    + TRANSLATION_MAP_TYPOGRAPHIC_UTF8_NORM
)


def lowunaccent(string_, normalized=False):

    string_ = string_.lower()

    tr_map = (
        TRANSLATION_MAP_LOWER_UTF8_NORM
        if normalized else TRANSLATION_MAP_LOWER
    )

    for elem, repl in tr_map:
        string_ = string_.replace(elem, repl)

    return string_


def asciize(stest, aggressive=False, maxlenght=128, custom_keep=None, replace_by=None):
    ''' Remove all special characters from a string.
        Replace accentuated letters with non-accentuated ones, replace spaces,
        lower the name, etc.

        .. todo:: use http://docs.python.org/library/string.html#string.translate
            , but this could be more complicated than it seems.
    '''

    if custom_keep is None:
        custom_keep = '-.'

    for elem, repl in TRANSLATION_MAP_FULL:
        stest = stest.replace(elem, repl)

    if not aggressive:
        # For this `.sub()`, any '-' in `custom_keep` must be the first char,
        # else the operation will fail with "bad character range".
        if '-' in custom_keep:
            custom_keep = '-' + custom_keep.replace('-', '')

    # We compile the expression to be able to use the `flags` argument,
    # which doesn't exist on Python 2.6 (cf.
    #                         http://dev.licorn.org/ticket/876#comment:3)
    cre = re.compile('[^{}a-z0-9]'.format(
        '.' if aggressive else custom_keep), flags=re.I)

    # delete any strange (or forgotten by translation map…) char left
    if aggressive:
        stest = cre.sub('', stest)

    else:
        # keep dashes (or custom characters)
        stest = cre.sub(replace_by or '', stest)

    # For next substitutions, we must be sure `custom_keep` doesn't
    # include "-" at all, else it will fail again with "bad character range".
    custom_keep = custom_keep.replace('-', '')

    # Strip remaining doubles punctuations signs
    stest = re.sub('([-._{0}])[-._{1}]*'.format(
        custom_keep, custom_keep), '\1', stest)

    # Strip left and rights punct signs
    stest = re.sub('(^[-._{0}]*|[-._{0}*]*$)'.format(
        custom_keep, custom_keep), '', stest)

    if len(stest) > maxlenght:
        raise BibedStringException(
            'String {0} too long ({1} characters, '
            'but must be shorter or equal than {2}).'.format(
                stest, len(stest), maxlenght))

    return stest


def seconds_to_string(elapsed):

    # See https://stackoverflow.com/a/12344609/654755

    return str(timedelta(seconds=elapsed))


def friendly_filename(filename):

    # the base name, without extension.
    return os.path.basename(filename).rsplit('.', 1)[0]


def to_lower_if_not_none(data):

    if data is None:
        return ''

    return data.lower()

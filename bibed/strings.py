
import os
import re
import base64

from bibed.exceptions import BibedStringException
from bibed.locale import _
from bibed.gtk import GLib


def b32encode(data):

    return base64.b32encode(data.encode('utf8')).decode('utf-8')


def b32decode(data):
    try:
        return base64.b32decode(
            data.encode('utf-8')
        ).decode('utf-8')

    except Exception:
        return data


def format_import_data(data):

    return data[:32] + (data[32:] and _('[…]'))


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


def friendly_filename(filename, translate=True):

    if translate:
        # the base name, without extension.
        # Translated on the fly, for system databases names.
        return _(os.path.basename(filename)).rsplit('.', 1)[0]

    return os.path.basename(filename).rsplit('.', 1)[0]


def to_lower_if_not_none(data):

    if data is None:
        return ''

    return data.lower()


def bibtex_clean(string_):

    return string_.replace(' {and} ', ' ').replace(' and ', ' ')


# —————————————————————————————————————————————— LaTeX to Pango Markup and back

LATEX_EXPR = r'[^}]+'
PANGO_EXPR = r'[^<]+'

L2P_TRANSFORMS = {
    # This is SOOOOO Basic… It won't even work for nested expressions…
    # Test expression:
    # t = r'1\textsuperscript{er} mois avec CH\textsubscript{3}Cl\textsubscript{2} et c\'est \textbf{super bien !} D\'ailleurs je \emph{crois} que \texttt{Gtk & Pango} c\'est vraiment \st{pas} \underline{Coolissime}.'
    # latex_to_pango_markup(t)
    # assert t == latex_to_pango_markup(latex_to_pango_markup(t), True)
    'superscript': (
        (re.compile(r'\\textsuperscript\{(' + LATEX_EXPR + r')\}'), r'<sup>\1</sup>', ),
        (re.compile(r'<sup>(' + PANGO_EXPR + r')</sup>'), r'\\textsuperscript{\1}', ),
    ),
    'subscript': (
        (re.compile(r'\\textsubscript\{(' + LATEX_EXPR + r')\}'), r'<sub>\1</sub>', ),
        (re.compile(r'<sub>(' + PANGO_EXPR + r')</sub>'), r'\\textsubscript{\1}', ),
    ),
    'bold': (
        (re.compile(r'\\textbf\{(' + LATEX_EXPR + r')\}'), r'<b>\1</b>', ),
        (re.compile(r'<b>(' + PANGO_EXPR + r')</b>'), r'\\textbf{\1}', ),
    ),
    'emphasis': (
        (re.compile(r'\\emph\{(' + LATEX_EXPR + r')\}'), r'<i>\1</i>', ),
        (re.compile(r'<i>(' + PANGO_EXPR + r')</i>'), r'\\emph{\1}', ),
    ),
    'monospace': (
        (re.compile(r'\\texttt\{(' + LATEX_EXPR + r')\}'), r'<tt>\1</tt>', ),
        (re.compile(r'<tt>(' + PANGO_EXPR + r')</tt>'), r'\\texttt{\1}', ),
    ),
    'underline': (
        (re.compile(r'\\underline\{(' + LATEX_EXPR + r')\}'), r'<u>\1</u>', ),
        (re.compile(r'<u>(' + PANGO_EXPR + r')</u>'), r'\\underline{\1}', ),
    ),
    'striked': (
        (re.compile(r'\\s(?:ou)?t\{(' + LATEX_EXPR + r')\}'), r'<s>\1</s>', ),
        # Note: this needs the latex `ulem` package, but it's
        #       completely out of Bibed's scope to check this…
        (re.compile(r'<s>(' + PANGO_EXPR + r')</s>'), r'\\sout{\1}', ),
    ),
    'links': (
        (re.compile(r'\\url\{(' + LATEX_EXPR + r')\}'), r'<a href="\1">\1</a>', ),
        # Note: this needs the latex `ulem` package, but it's
        #       completely out of Bibed's scope to check this…
        (re.compile(r'<a href[^>]+>(' + PANGO_EXPR + r')</a>'), r'\\url{\1}', ),
    ),
}


def latex_to_pango_markup(text, reverse=False):

    index = 1 if reverse else 0

    for key, value in L2P_TRANSFORMS.items():

        regex, repl = value[index]

        text = regex.sub(repl, text)

    return text

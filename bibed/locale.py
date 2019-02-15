
import sys
import os
from os import environ
import locale
import gettext

from bibed.foundations import (
    BIBED_DATA_DIR,
    xdg_get_system_data_dirs,
)
from bibed.ltrace import lprint
from bibed.utils import (
    is_windows,
    is_osx,
)

# —————————————————————————————————————————————————————————————— Module globals

__translation = None

# ————————————————————————————————————————————————————————————————————— Classes


class GlibTranslations(gettext.GNUTranslations):
    '''Provide a glib-like translation API for Python.

    This class adds support for pgettext (and upgettext) mirroring
    glib's C_ macro, which allows for disambiguation of identical
    source strings.

    It can also be instantiated and used with any valid MO files
    (though it won't be able to translate anything, of course).
    '''

    def __init__(self, fp=None):

        self.path = (fp and fp.name) or ""
        self._catalog = {}
        self.plural = lambda n: n != 1
        gettext.GNUTranslations.__init__(self, fp)
        self._debug_text = None

    def ugettext(self, message):
        # force unicode here since __contains__ (used in gettext) ignores
        # our changed defaultencoding for coercion, so utf-8 encoded strings
        # fail at lookup.
        message = str(message)
        return str(gettext.GNUTranslations.gettext(self, message))

    def ungettext(self, msgid1, msgid2, n):
        # see ugettext
        msgid1 = str(msgid1)
        msgid2 = str(msgid2)
        return str(
            gettext.GNUTranslations.ngettext(self, msgid1, msgid2, n))

    def unpgettext(self, context, msgid, msgidplural, n):
        context = str(context)
        msgid = str(msgid)
        msgidplural = str(msgidplural)
        real_msgid = u"%s\x04%s" % (context, msgid)
        real_msgidplural = u"%s\x04%s" % (context, msgidplural)
        result = self.ngettext(real_msgid, real_msgidplural, n)
        if result == real_msgid:
            return msgid
        elif result == real_msgidplural:
            return msgidplural
        return result

    def upgettext(self, context, msgid):
        context = str(context)
        msgid = str(msgid)
        real_msgid = u"%s\x04%s" % (context, msgid)
        result = self.ugettext(real_msgid)
        if result == real_msgid:
            return msgid
        return result

    def set_debug_text(self, debug_text):
        self._debug_text = debug_text

    def wrap_text(self, value):
        if self._debug_text is None:
            return value
        else:
            return self._debug_text + value + self._debug_text

    def install(self, *args, **kwargs):
        raise NotImplementedError("We no longer do builtins")


# ——————————————————————————————————————————————————————————————————— functions


def bcp47_to_language(code):
    """Takes a BCP 47 language identifier and returns a value suitable for the
    LANGUAGE env var.

    Only supports a small set of inputs and might return garbage..
    """

    if code == 'zh-Hans':
        return 'zh_CN'

    elif code == 'zh-Hant':
        return 'zh_TW'

    parts = code.split('-')
    is_iso = lambda s: len(s) == 2 and s.isalpha()  # NOQA

    # we only support ISO 639-1
    if not is_iso(parts[0]):
        return parts[0].replace(':', '')

    lang_subtag = parts[0]

    region = ''
    if len(parts) >= 2 and is_iso(parts[1]):
        region = parts[1]

    elif len(parts) >= 3 and is_iso(parts[2]):
        region = parts[2]

    if region:
        return '{}_{}'.format(lang_subtag, region)

    return lang_subtag


def osx_locale_id_to_lang(id_):
    """Converts a NSLocale identifier to something suitable for LANG"""

    if '_' not in id_:
        return id_
    # id_ can be "zh-Hans_TW"
    parts = id_.rsplit('_', 1)
    ll = parts[0]
    ll = bcp47_to_language(ll).split('_')[0]
    return '{}_{}'.format(ll, parts[1])


def set_i18n_envvars():
    """Set the LANG/LANGUAGE environment variables if not set in case the
    current platform doesn't use them by default (OS X, Window)
    """

    if is_windows():
        from quodlibet.util.winapi import GetUserDefaultUILanguage, \
            GetSystemDefaultUILanguage

        langs = list(filter(None, map(locale.windows_locale.get,
                                      [GetUserDefaultUILanguage(),
                                       GetSystemDefaultUILanguage()])))
        if langs:
            environ.setdefault('LANG', langs[0])
            environ.setdefault('LANGUAGE', ':'.join(langs))

    elif is_osx():
        from AppKit import NSLocale
        locale_id = NSLocale.currentLocale().localeIdentifier()
        lang = osx_locale_id_to_lang(locale_id)
        environ.setdefault('LANG', lang)

        preferred_langs = NSLocale.preferredLanguages()
        if preferred_langs:
            languages = map(bcp47_to_language, preferred_langs)
            environ.setdefault('LANGUAGE', ':'.join(languages))
    else:
        return


def fixup_i18n_envvars():
    """Sanitizes env vars before gettext can use them.

    LANGUAGE should support a priority list of languages with fallbacks, but
    doesn't work due to "en" no being known to gettext (This could be solved
    by providing a en.po in QL but all other libraries don't define it either)

    This tries to fix that.
    """

    try:
        langs = environ['LANGUAGE'].split(':')

    except KeyError:
        return

    # So, this seems to be an undocumented feature where C selects
    # "no translation". Append it to any en/en_XX so that when not found
    # it falls back to "en"/no translation.
    sanitized = []

    for lang in langs:
        sanitized.append(lang)
        if lang.startswith('en') and len(langs) > 1:
            sanitized.append('C')

    environ['LANGUAGE'] = ':'.join(sanitized)


def iter_locale_dirs():

    dirs = list(xdg_get_system_data_dirs())

    # this is the one python gettext uses by default, use as a fallback
    dirs.append(os.path.join(sys.base_prefix, "share"))

    done = set()
    for path in dirs:
        locale_dir = os.path.join(path, "locale")

        if locale_dir in done:
            continue

        done.add(locale_dir)

        if os.path.isdir(locale_dir):
            yield locale_dir


def register_translation(domain, localedir=None):
    """Register a translation domain

    Args:
        domain (str): the gettext domain
        localedir (pathlike): A directory used for translations, if None the
            system one will be used.
    Returns:
        GlibTranslations
    """

    if localedir is None:
        iterdirs = iter_locale_dirs

    else:
        iterdirs = lambda: iter([localedir])  # NOQA

    for dir_ in iterdirs():
        try:
            t = gettext.translation(domain, dir_, class_=GlibTranslations)

        except OSError:
            continue

        else:
            lprint('Translations loaded: {}', t.path)
            break
    else:
        lprint('No translation found for the domain {}', domain)
        t = GlibTranslations()

    return t


def init():

    global __translation

    set_i18n_envvars()
    fixup_i18n_envvars()

    lprint('LANGUAGE: {}'.format(environ.get('LANGUAGE')))
    lprint('LANG: {}'.format(environ.get('LANG')))

    try:
        locale.setlocale(locale.LC_ALL, '')

    except locale.Error:
        pass

    # XXX: these are our most user facing APIs, make sre they are not loaded
    # before we set the language. For GLib this is too late..
    assert "gi.repository.Gtk" not in sys.modules
    assert "gi.repository.Gst" not in sys.modules

    # Use the locale dir in ../build/share/locale if there is one
    localedir = os.path.join(
        os.path.dirname(BIBED_DATA_DIR), 'locale')

    if not os.path.isdir(localedir):
        localedir = None

    __translation = register_translation('bibed', localedir)


def _(message):
    """
    Args:
        message (str)
    Returns:
        str

    Lookup the translation for message
    """

    return __translation.wrap_text(__translation.ugettext(message))


def NO_(message):
    """
    Args:
        message (str)
    Returns:
        str

    Only marks a string for translation
    """

    return str(message)


def C_(context, message):
    """
    Args:
        context (str)
        message (str)
    Returns:
        str

    Lookup the translation for message for a context
    """

    return __translation.wrap_text(__translation.upgettext(context, message))


def n_(singular, plural, n):
    """
    Args:
        singular (str)
        plural (str)
        n (int)
    Returns:
        str

    Returns the translation for a singular or plural form depending
    on the value of n.
    """

    return __translation.wrap_text(__translation.ungettext(singular, plural, n))


def numeric_phrase(singular, plural, n, template_var=None):
    """Returns a final locale-specific phrase with pluralisation if necessary
    and grouping of the number.

    This is added to custom gettext keywords to allow us to use as-is.

    Args:
        singular (str)
        plural (str)
        n (int)
        template_var (str)
    Returns:
        str

    For example,

    ``numeric_phrase('Add %d song', 'Add %d songs', 12345)``
    returns
    `"Add 12,345 songs"`
    (in `en_US` locale at least)
    """
    num_text = locale.format_string('%d', n, grouping=True)

    if not template_var:
        template_var = '%d'
        replacement = '%s'
        params = num_text

    else:
        template_var = '%(' + template_var + ')d'
        replacement = '%(' + template_var + ')s'
        params = dict()
        params[template_var] = num_text

    return (n_(singular, plural, n).replace(template_var, replacement) %
            params)


def np_(context, singular, plural, n):

    return __translation.wrap_text(__translation.unpgettext(context, singular, plural, n))


__all__ = (
    init,
    _,
    NO_, C_,
    n_, np_,
    numeric_phrase,
)

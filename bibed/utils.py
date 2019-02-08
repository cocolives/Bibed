
import os
import re
import logging
import webbrowser
import subprocess

from bibed.constants import (
    PREFERENCES_FILENAME,
    MEMORIES_FILENAME,
    BIBED_APP_DIR_POSIX,
    BIBED_APP_DIR_WIN32,
)

from bibed.exceptions import ActionError

from bibed.foundations import (
    is_osx, is_windows,
    lprint_caller_name,
    lprint_function_name,
    AttributeDict,
    AttributeDictFromYaml,
    Singleton,
)

LOGGER = logging.getLogger(__name__)

TRANSLATION_MAP = (
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

    # no-special-case chars
    ('ß', 'ss'), ('þ', ''), ('ð', ''), ('µ', ''), ('$', ''),
    ('€', ''), ('§', ''), ('~', ''), ('&', ''), ('/', ''), ('=', ''),

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


# ————————————————————————————————————————————————————————————— Functions

def get_user_home_directory():

    # https://stackoverflow.com/a/10644400/654755

    if is_windows():
        from win32com.shell import shellcon, shell
        home_dir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)

    else:
        # os.environ['HOME'] is OK too.
        home_dir  = os.path.expanduser('~')

    return home_dir


def get_bibed_user_dir():
    ''' OS-dependant storage directory. '''

    if is_windows():
        bibed_base_dir = BIBED_APP_DIR_WIN32

    else:
        bibed_base_dir = BIBED_APP_DIR_POSIX

    bibed_dir = os.path.join(get_user_home_directory(), bibed_base_dir)

    return bibed_dir


def make_bibed_user_dir():

    bibed_user_dir = get_bibed_user_dir()

    try:
        os.makedirs(bibed_user_dir)

    except FileExistsError:
        pass

    except Exception:
        LOGGER.exception(
            'While creating preferences directory “{}”'.format(bibed_user_dir))


def open_urls_in_web_browser(urls):

    for url in urls:
        webbrowser.open_new_tab(url)


def open_with_system_launcher(filenames):

    if is_osx():
        base_command = ['open']

    elif is_windows():
        base_command = ['start']

    else:
        # Linux
        base_command = ['xdg-open']

    for filename in filenames:
        if filename.startswith(':') and filename.lower().endswith(':pdf'):
            # get rid of older filenames like “:/home/olive/myfile.pdf:PDF”
            filename = filename[1:-4]

        try:
            # This will raise an exception if any error is encountered.
            subprocess.check_call(base_command + [filename])

        except Exception:
            raise ActionError(' '.join(command))


def friendly_filename(filename):

    # the base name, without extension.
    return os.path.basename(filename).rsplit('.', 1)[0]


def to_lower_if_not_none(data):

    if data is None:
        return ''

    return data.lower()


def asciize(stest, aggressive=False, maxlenght=128, custom_keep=None, replace_by=None):
    ''' Remove all special characters from a string.
        Replace accentuated letters with non-accentuated ones, replace spaces,
        lower the name, etc.

        .. todo:: use http://docs.python.org/library/string.html#string.translate
            , but this could be more complicated than it seems.
    '''

    if custom_keep is None:
        custom_keep = '-.'

    for elem, repl in TRANSLATION_MAP:
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


# ———————————————————————————————————————————————————————————————— Classes


class ApplicationDefaults(AttributeDictFromYaml, metaclass=Singleton):
    filename = os.path.join(os.path.dirname(
                            os.path.abspath(__file__)),
                            'data',
                            PREFERENCES_FILENAME)


class UserPreferences(AttributeDictFromYaml, metaclass=Singleton):
    filename = os.path.join(get_bibed_user_dir(),
                            PREFERENCES_FILENAME)

    def __init__(self, defaults, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # bypass classic attribute setter
        # to avoid YAML dumping of that.
        self.__dict__['defaults'] = defaults

        if self.accelerators is None:
            self.accelerators = AttributeDict(default=True)

        if self.fields is None:
            self.fields = AttributeDict(default=True)

        if self.types is None:
            self.types = AttributeDict(default=True)


class UserMemories(AttributeDictFromYaml, metaclass=Singleton):
    filename = os.path.join(get_bibed_user_dir(),
                            MEMORIES_FILENAME)

    def __init__(self, defaults, preferences, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # bypass classic attribute setter
        # to avoid YAML dumping of that.
        self.__dict__['defaults'] = defaults
        self.__dict__['preferences'] = preferences

    def add_open_file(self, filename):

        # assert lprint_function_name()

        if self.open_files is None:
            self.open_files = set((filename, ))

        else:
            self.open_files |= set((filename,))

    def remove_open_file(self, filename):

        # assert lprint_function_name()

        if self.open_files is not None:
            try:
                self.open_files.remove(filename)

            except ValueError:
                pass

            else:
                # Typical case of impossible auto_save…
                self.save()

    def add_recent_file(self, filename):

        # assert lprint_function_name()

        defs  = self.defaults
        prefs = self.preferences

        if self.recent_files is not None:
            try:
                # In case we already opened it recently,
                # remove it first from history to reput
                # it at list beginning.
                self.recent_files.remove(filename)

            except ValueError:
                # Not in list.
                pass

            self.recent_files.insert(0, filename)

            # TODO: be sure this is an int(). In the past,
            # I didn't force int() in the preference dialog.
            max = (
                defs.keep_recent_files
                if prefs.keep_recent_files is None
                else prefs.keep_recent_files
            )

            # This will automatically trigger a save().
            self.recent_files = self.recent_files[:max]

        else:
            # This will trigger auto_save.
            self.recent_files = [filename]

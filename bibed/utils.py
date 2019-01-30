
import os
import logging
import pyinotify

from bibed.constants import (
    PREFERENCES_FILENAME,
    MEMORIES_FILENAME,
    BIBED_APP_DIR_POSIX,
    BIBED_APP_DIR_WIN32,
)

from bibed.foundations import (
    AttributeDict,
    AttributeDictFromYaml,
    Singleton,
)


LOGGER = logging.getLogger(__name__)


# ————————————————————————————————————————————————————————————— Functions


def get_user_home_directory():

    # https://stackoverflow.com/a/10644400/654755

    if os.name != 'posix':
        from win32com.shell import shellcon, shell
        home_dir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)

    else:
        # os.environ['HOME'] is OK too.
        home_dir  = os.path.expanduser('~')

    return home_dir


def get_bibed_user_dir():
    ''' OS-dependant storage directory. '''

    if os.name != 'posix':
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


def to_lower_if_not_none(data):

    if data is None:
        return ''

    return data.lower()


# ———————————————————————————————————————————————————————————————— Classes


class PyinotifyEventHandler(pyinotify.ProcessEvent):

    app = None

    def process_IN_MODIFY(self, event):

        if __debug__:
            LOGGER.debug('Modify event start ({}).'.format(event.pathname))

        PyinotifyEventHandler.app.on_file_modify(event)

        if __debug__:
            LOGGER.debug('Modify event end ({}).'.format(event.pathname))

        return True


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

        if self.open_files is None:
            self.open_files = set((filename, ))

        else:
            self.open_files |= set((filename,))

    def remove_open_file(self, filename):

        if self.open_files is not None:
            try:
                self.open_files.remove(filename)

            except ValueError:
                pass

            else:
                # Typical case of impossible auto_save…
                self.save()

    def add_recent_file(self, filename):

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

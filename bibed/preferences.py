
import os
import logging

from bibed.foundations import Singleton, AttributeDict
from bibed.yaml import AttributeDictFromYaml
from bibed.user import get_bibed_user_dir

LOGGER = logging.getLogger(__name__)


PREFERENCES_FILENAME = 'bibed.yaml'
MEMORIES_FILENAME    = 'memories.yaml'


# —————————————————————————————————————————————————————————————— Functions


def gpod(preference_name):
    ''' Get preference, or default if preference is not set.

        .note:: This only works for 1st-level preferences (eg.
            `preferences.remember_open_files`). As of 2019-01-23, this
            function is not sub-level capable. In most cases, sublevels
            need dedicated handlers, anyway.
    '''

    assert '.' not in preference_name, preference_name

    pref = getattr(preferences, preference_name)

    if pref is None:
        return getattr(defaults, preference_name)

    return pref

# ————————————————————————————————————————————————————————————————————— Classes


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


# —————————————————————————————————————————————————————— Preferences singletons


defaults    = ApplicationDefaults()
preferences = UserPreferences(defaults=defaults)
memories    = UserMemories(defaults=defaults,
                           preferences=preferences)

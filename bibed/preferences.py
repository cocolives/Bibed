
import logging

from bibed.utils import (
    make_bibed_user_dir,
    ApplicationDefaults,
    UserPreferences,
    UserMemories,
)

LOGGER = logging.getLogger(__name__)


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


# ————————————————————————————————————————————————— preferences singletons


make_bibed_user_dir()


defaults    = ApplicationDefaults()
preferences = UserPreferences(defaults=defaults)
memories    = UserMemories(defaults=defaults,
                           preferences=preferences)

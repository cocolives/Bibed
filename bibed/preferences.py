
import logging

from bibed.utils import (
    make_bibed_user_dir,
    ApplicationDefaults,
    UserPreferences,
    UserMemories,
)

LOGGER = logging.getLogger(__name__)


# —————————————————————————————————————————————————————————————— Functions

def gpod(pref_name):

    pref = getattr(preferences, pref_name)

    if pref is None:
        return getattr(defaults, pref_name)

    return pref


# ————————————————————————————————————————————————— preferences singletons


make_bibed_user_dir()


defaults    = ApplicationDefaults()
preferences = UserPreferences(defaults=defaults)
memories    = UserMemories(defaults=defaults,
                           preferences=preferences)


import logging

from bibed.utils import (
    make_bibed_user_dir,
    ApplicationDefaults,
    UserPreferences,
    UserMemories,
)

LOGGER = logging.getLogger(__name__)


# ————————————————————————————————————————————————— preferences singletons


make_bibed_user_dir()


defaults    = ApplicationDefaults()
preferences = UserPreferences(defaults=defaults)
memories    = UserMemories(defaults=defaults,
                           preferences=preferences)


import logging

from bibed.constants import (
    APP_VERSION,
)

from bibed.preferences import gpod
from bibed.foundations import Singleton

LOGGER = logging.getLogger(__name__)


class SentryHelper(metaclass=Singleton):

    def __init__(self):

        self.__enabled = False

        try:
            import sentry_sdk  # NOQA

        except Exception:
            LOGGER.exception('Unable to import sentry SDK. '
                             'Errors will not be reported.')
            self.__usable = False

        else:
            self.__usable = True

    @property
    def usable(self):

        return self.__usable and self.__enabled

    def enable(self):

        if self.__enabled:
            return

        if not self.__usable:
            return

        import sentry_sdk

        sentry_dsn = gpod('sentry_dsn')

        sentry_sdk.init(sentry_dsn, release=APP_VERSION)

        LOGGER.info('Using sentry to report errors to {}'.format(sentry_dsn))

        self.__enabled = True

    def disable(self):

        if not self.__enabled:
            return

        try:
            import sentry_sdk

        except Exception:
            LOGGER.error('Unable to import sentry SDK.')
            return

        # _initial_client is a weakref. Call it.
        client = sentry_sdk.hub._initial_client()

        # According to the documentation, this does what we need.
        # https://getsentry.github.io/sentry-python/#sentry_sdk.Client.close
        client.close()

        LOGGER.info('Disabled sentry error reporting.')

        self.__enabled = False


sentry = SentryHelper()

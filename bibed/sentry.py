
import logging

from bibed.constants import (
    APP_VERSION,
)

from bibed.preferences import gpod
from bibed.foundations import Singleton

LOGGER = logging.getLogger(__name__)


class SentryHelper(metaclass=Singleton):

    def __init__(self):

        self.enabled = False

    def enable(self):

        if self.enabled:
            return

        try:
            import sentry_sdk

        except Exception:
            LOGGER.error('Unable to import sentry SDK. '
                         'Errors will not be reported.')
            return

        sentry_dsn = gpod('sentry_dsn')

        sentry_sdk.init(sentry_dsn, release=APP_VERSION)

        LOGGER.info('Using sentry to report errors to {}'.format(sentry_dsn))

        self.enabled = True

    def disable(self):

        if not self.enabled:
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

        self.enabled = False

sentry = SentryHelper()

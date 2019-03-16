''' The bare minimal things needed for Bibed core to run properly. '''

import sys
import time
import logging
import multiprocessing


LOGGER = logging.getLogger(__name__)


__all__ = (
    'app_main',
    'minimal_setup',
)

def minimal_setup(load_system_files=True):
    ''' Sets up logging, locale & controllers with system files.
        Returns logging handlers (as a :class:`list`).

        Used in importer tests, background process…
    '''

    from bibed.logging import setup_logging
    from bibed.locale import init as locale_init

    if __debug__:
        logging_handlers = setup_logging(logging.DEBUG)
    else:
        logging_handlers = setup_logging(logging.INFO)

    locale_init()

    if load_system_files:
        from bibed.controllers import controllers
        controllers.files.load_system_files()

    return logging_handlers


def app_main():
    ''' Main Gtk application startup function, run by the desktop executable. '''

    time_start = time.time()

    # See app.py and daemon.py + spawn.py for the remaining.
    multiprocessing.set_start_method('spawn')
    multiprocessing.current_process().name = 'Bibed'

    # System files will be loaded by the
    # app, after the data store is setup.
    logging_handlers = minimal_setup(load_system_files=False)

    # Needs to be after setup_logging(),
    # else we miss a lot of message.
    from bibed.parallel import run_and_wait_on
    from bibed.dtu import seconds_to_string
    from bibed.gtk import Gtk  # NOQA
    from bibed.gui.splash import start_splash
    from bibed.app import BibedApplication
    from bibed.preferences import gpod
    from bibed.sentry import sentry
    from bibed.locale import _

    splash = start_splash()

    if gpod('use_sentry'):
        splash.set_status(
            _('Connecting issue collector to {}…').format(
                gpod('sentry_url')))

        run_and_wait_on(sentry.enable)

        if __debug__:
            assert sentry.usable

            import sentry_sdk
            try:
                raise Exception('Test exception Bibed')

            except Exception:
                sentry_sdk.capture_exception()

        LOGGER.debug('Sentry startup time: {}'.format(
            seconds_to_string(time.time() - time_start)))

    app = BibedApplication(time_start=time_start, splash=splash,
                           logging_handlers=logging_handlers)

    exit_status = app.run(sys.argv)
    sys.exit(exit_status)


import time
import functools
import logging

from bibed.gtk import GLib, Gtk
from bibed.strings import seconds_to_string

LOGGER = logging.getLogger(__name__)
FUNC_IDLE_CALLS = {}
FUNC_MOST_CALLS = {}


def build_signature(func, args, limit=None):
    ''' Very simple signature generator, hard-assuming how I use the decorators. '''

    if limit is None:
        # with "2", we get self and first argument.
        # In most of our uses cases this is sufficient.
        limit = 2

    return '{}{}'.format(
        func.__name__,
        ''.join(
            str(id(arg))
            for arg in args[:limit]
        )
    )


def only_one_when_idle(func):
    ''' Stack a burst of calls of one function, and execute it only once. '''

    @functools.wraps(func)
    def wrapper(*args):

        signature = build_signature(func, args)

        if signature in FUNC_IDLE_CALLS:
            # Already in idle queue
            return

        def run_and_remove():

            func(*args)

            GLib.source_remove(FUNC_IDLE_CALLS[signature])
            del FUNC_IDLE_CALLS[signature]

        FUNC_IDLE_CALLS[signature] = GLib.idle_add(run_and_remove)

    return wrapper


def run_at_most_every(delay):
    ''' Execute :param:`func` at most every :param:`delay`.

        :param delay: integer, must comply to :func:`Glib.timeout_add`.
    '''

    def decorator(func):

        @functools.wraps(func)
        def wrapper(*args):

            signature = build_signature(func, args)

            if signature in FUNC_MOST_CALLS:
                try:
                    GLib.source_remove(FUNC_MOST_CALLS[signature])

                except Exception:
                    # Obsolete source. It's like it wasn't there.
                    del FUNC_MOST_CALLS[signature]

            def run_and_remove():

                func(*args)

                GLib.source_remove(FUNC_MOST_CALLS[signature])
                del FUNC_MOST_CALLS[signature]

                # Be sure the function will not be re-run.
                return False

            FUNC_MOST_CALLS[signature] = GLib.timeout_add(delay, run_and_remove)

        return wrapper

    return decorator


def wait_for_queued_events(delay=None):

    start = time.time()

    if delay is None:
        # defaults to 10 seconds (some methods
        # can be delayed once every 5 secs).
        delay = 10000

    wait_cycle = 0
    has_remaining = 0

    if FUNC_IDLE_CALLS or FUNC_MOST_CALLS:
        has_remaining = len(FUNC_IDLE_CALLS) + len(FUNC_MOST_CALLS)
        LOGGER.info(
            'Waiting at most {:.1f} seconds for {} remaining '
            'events to run…'.format(delay / 1000, has_remaining))

    while (FUNC_IDLE_CALLS or FUNC_MOST_CALLS) and wait_cycle != delay:

        while Gtk.events_pending():
            Gtk.main_iteration()

        wait_cycle += 1
        time.sleep(0.001)

    if FUNC_IDLE_CALLS:
        LOGGER.warning('Idle calls still pending: {}'.format(
            len(FUNC_IDLE_CALLS)
        ))

    elif FUNC_MOST_CALLS:
        LOGGER.warning('Timeout calls still pending: {}'.format(
            len(FUNC_MOST_CALLS)
        ))

    elif has_remaining:
        LOGGER.info('Last {} remaining events ran in {} secs.'.format(
            has_remaining, seconds_to_string(time.time() - start)))

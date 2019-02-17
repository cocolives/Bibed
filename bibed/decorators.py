
import functools

from bibed.gtk import GLib


FUNC_IDLE_CALLS = {}
FUNC_MOST_CALLS = {}


def only_one_when_idle(func):
    ''' Stack a burst of calls of one function, and execute it only once. '''

    @functools.wraps(func)
    def wrapper(*args):

        if func.__name__ in FUNC_IDLE_CALLS:
            try:
                GLib.source_remove(FUNC_IDLE_CALLS[func.__name__])

            except Exception:
                # Obsolete source. It's like it wasn't there.
                del FUNC_IDLE_CALLS[func.__name__]

        def run_and_remove():

            func(*args)

            GLib.source_remove(FUNC_IDLE_CALLS[func.__name__])
            del FUNC_IDLE_CALLS[func.__name__]

        FUNC_IDLE_CALLS[func.__name__] = GLib.idle_add(run_and_remove)

    return wrapper


def run_at_most_every(delay):
    ''' Execute :param:`func` at most every :param:`delay`.

        :param delay: integer, must comply to :func:`Glib.timeout_add`.
    '''

    def decorator(func):

        @functools.wraps(func)
        def wrapper(*args):

            if func.__name__ in FUNC_MOST_CALLS:
                try:
                    GLib.source_remove(FUNC_MOST_CALLS[func.__name__])

                except Exception:
                    # Obsolete source. It's like it wasn't there.
                    del FUNC_MOST_CALLS[func.__name__]

            def run_and_remove():

                func(*args)

                GLib.source_remove(FUNC_MOST_CALLS[func.__name__])
                del FUNC_MOST_CALLS[func.__name__]

                # Be sure the function will not be re-run.
                return False

            FUNC_MOST_CALLS[func.__name__] = GLib.timeout_add(delay, run_and_remove)

        return wrapper

    return decorator

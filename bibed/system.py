
import sys
import os
import logging
import ctypes
import ctypes.util


LOGGER = logging.getLogger(__name__)


def is_osx():

    return sys.platform == 'darwin'


def is_windows():

    return os.name != 'posix'


def load_library(names, shared=True):
    """Load a ctypes library with a range of names to try.

    Handles direct .so names and library names ["libgpod.so", "gpod"].

    If shared is True can return a shared instance.
    Raises OSError if not found.

    Returns (library, name)
    """

    if not names:
        raise ValueError

    if shared:
        load_func = lambda n: getattr(ctypes.cdll, n)  # NOQA
    else:
        load_func = ctypes.cdll.LoadLibrary

    errors = []
    for name in names:
        dlopen_name = name
        if ".so" not in name and ".dll" not in name and \
                ".dylib" not in name:
            dlopen_name = ctypes.util.find_library(name) or name

        if is_osx() and not os.path.isabs(dlopen_name):
            dlopen_name = os.path.join(sys.prefix, "lib", dlopen_name)

        try:
            return load_func(dlopen_name), name
        except OSError as e:
            errors.append(str(e))

    raise OSError("\n".join(errors))


def set_process_title(title):
    """Sets process name as visible in ps or top. Requires ctypes libc
        and is almost certainly *nix-only.
    """

    if os.name == "nt":
        return

    try:
        libc = load_library(["libc.so.6", "c"])[0]
        prctl = libc.prctl

    except (OSError, AttributeError):
        LOGGER.error(
            "Couldn't find module libc.so.6 (ctypes). "
            "Not setting process title.")
    else:
        prctl.argtypes = [
            ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
            ctypes.c_ulong, ctypes.c_ulong,
        ]
        prctl.restype = ctypes.c_int

        PR_SET_NAME = 15
        data = ctypes.create_string_buffer(title.encode("utf-8"))
        res = prctl(PR_SET_NAME, ctypes.addressof(data), 0, 0, 0)

        if res != 0:
            sys.sdterr.write("Setting the process title failed.")


def touch_file(filename):
    ''' Create a file (containing a newline) if missing. '''

    # TODO: touch the file if already existing.

    # assert lprint_caller_name()
    # assert lprint(filename)

    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            f.write('\n')

        LOGGER.debug('touch_file(): created “{}”.'.format(filename))


def xdg_get_system_data_dirs():
    ''' http://standards.freedesktop.org/basedir-spec/latest/ '''

    if is_windows():
        from gi.repository import GLib
        dirs = []

        for dir_ in GLib.get_system_data_dirs():
            # TODO: glib2fsn(dir_)
            dirs.append(dir_)

        return dirs

    data_dirs = os.getenv('XDG_DATA_DIRS')

    if data_dirs:
        return list(map(os.path.abspath, data_dirs.split(':')))

    else:
        return ('/usr/local/share/', '/usr/share/')

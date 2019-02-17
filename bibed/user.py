
import sys
import os

from bibed.system import (
    is_windows,
    # is_osx,
)

# User application data (eg. preferences folder)
BIBED_APP_DIR_WIN32  = 'Bibed'
BIBED_APP_DIR_POSIX  = '.config/bibed'

# ——————————————————————————————————————————————————————————————————— functions


def get_user_home_directory():

    # https://stackoverflow.com/a/10644400/654755

    if is_windows():
        from win32com.shell import shellcon, shell
        home_dir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)

    else:
        # os.environ['HOME'] is OK too.
        home_dir  = os.path.expanduser('~')

    return home_dir


def get_bibed_user_dir():
    ''' OS-dependant storage directory. '''

    if is_windows():
        bibed_base_dir = BIBED_APP_DIR_WIN32

    else:
        bibed_base_dir = BIBED_APP_DIR_POSIX

    bibed_dir = os.path.join(get_user_home_directory(), bibed_base_dir)

    return bibed_dir


def make_bibed_user_dir():

    bibed_user_dir = get_bibed_user_dir()

    for folder in (bibed_user_dir, BIBED_LOG_DIR):
        try:
            os.makedirs(folder)

        except FileExistsError:
            pass

        except Exception:
            sys.stderr.write(
                'Could not create preferences directory “{}”.'.format(
                    bibed_user_dir))
            raise SystemExit(1)


BIBED_LOG_DIR = os.path.join(get_bibed_user_dir(), 'logs', )
BIBED_LOG_FILE = os.path.join(BIBED_LOG_DIR, 'bibed.log')


# Make the dirs at first module import. Logfile needs it.
make_bibed_user_dir()

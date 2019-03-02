
import sys
import os
import gzip
import logging

from bibed.user import BIBED_LOG_FILE


logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('pyinotify').setLevel(logging.CRITICAL)
logging.getLogger('bibtexparser').setLevel(logging.CRITICAL)


class GZipNamer:

    def __call__(self, default_filename):

        return default_filename + '.gz'


class GZipRotator:
    ''' Inspired from https://stackoverflow.com/a/16461440/654755 '''

    def __call__(self, source, destination):

        os.rename(source, destination)

        gziped_destination = '{}.gz'.format(destination)

        with open(destination, 'rb') as file_in, \
                gzip.open(gziped_destination, 'wb') as file_out:
            file_out.writelines(file_in)

        os.rename(gziped_destination, destination)


def setup_logging(level=logging.INFO):

    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s')

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    rfh = logging.handlers.RotatingFileHandler(BIBED_LOG_FILE, backupCount=10)
    # File log is always full debug level
    # in case we need it to assist users.
    rfh.setLevel(logging.DEBUG)
    rfh.setFormatter(formatter)
    rfh.rotator = GZipRotator()
    rfh.namer = GZipNamer()

    # Rotate logs at every application launch.
    rfh.doRollover()

    mh = logging.handlers.MemoryHandler(32768)
    mh.setTarget(rfh)

    root.addHandler(mh)

    return (mh, rfh)

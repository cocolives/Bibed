
import sys
import os
import ctypes
import ctypes.util
import yaml
import gzip
import logging

from yaml.representer import Representer

from bibed.ltrace import ldebug


#
# HEADS UP: do NOT import constants here.
#


LOGGER = logging.getLogger(__name__)


#  local constants, imported in bied.constants

# Application data (eg. /usr/share/bibed/data)
BIBED_DATA_DIR = os.path.join(os.path.realpath(
    os.path.abspath(os.path.dirname(__file__))), 'data')
BIBED_ICONS_DIR = os.path.join(BIBED_DATA_DIR, 'icons')


# ——————————————————————————————————————————————————————————————————— Functions


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


# ————————————————————————————————————————————————————————————————————— Classes

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


class Singleton(type):
    ''' https://stackoverflow.com/q/6760685/654755 '''

    _instances = {}

    def __call__(cls, *args, **kwargs):

        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton,
                                        cls).__call__(*args, **kwargs)

            # assert ldebug('__call__ Singleton for {0}.', cls.__name__)

        return cls._instances[cls]


class Anything:
    ''' An object that can have any attribute.

        Made to merge an Enum and Gtk.ListStore args.
    '''

    def __init__(self, store_args_list=None):
        '''
            :param store_args_list: an iterable of strings, of which any will be
                set as attribute of self with incremental integer value.
                This is useful to build named enums.
        '''
        if store_args_list:
            self.__store_args = []

            for index, arg in enumerate(store_args_list):
                arg_name, arg_type = arg
                setattr(self, arg_name, index)
                self.__store_args.append(arg_type)

    @property
    def as_store_args(self):
        return self.__store_args[:]


class AttributeDict(object):
    """
    A class to convert a nested Dictionary into an object with key-values
    accessibly using attribute notation (AttributeDict.attribute) instead
    of key notation (Dict["key"]). This class recursively sets Dicts to
    objects, allowing you to recurse down nested dicts (like:
    AttributeDict.attr.attr).

    Karmak23 additions: the object is back dumpable to YAML, if you use
        the YAML representer_dict() explicitly on its class. See subclass
        `AttributeDictFromYaml` for a real-life example.

    Cf. http://databio.org/posts/python_AttributeDict.html
    and https://github.com/databio/pypiper/blob/master/pypiper/AttributeDict.py
    """

    def __init__(self, entries=None, default=False, *args, **kwargs):
        """
        :param entries: A dictionary (key-value pairs) to add as
            attributes.
        :param default: Should this AttributeDict object return default
            values for attributes that it does not have? If True, then
            `AttributeDict.my_prop` would return `None` instead of raising
            an error, if no `.my_prop` attribute were found.
        """

        # Don't forget other classes…
        super().__init__(*args, **kwargs)

        if entries is not None:
            self.add_entries(entries, default)

        # bypass __setattr__ to avoid loop. These 2
        # attributes will not be dumped back to YAML.
        self.__dict__['return_defaults'] = default
        # needs to copy() the keys() to new list else
        # it stores the reference to "dict_keys".
        if entries is None:
            self.__dict__['keys_to_dump'] = []
        else:
            self.__dict__['keys_to_dump'] = [x for x in entries]

    def add_entries(self, entries, default=False):
        ''' Convert `entries` to attributes, creating
            `:class:AttributeDict` on the fly when relevant. '''

        for key, value in entries.items():
            if type(value) is dict:
                self.__dict__[key] = AttributeDict(value, default)

            else:
                try:
                    # try expandvars() to allow the yaml to use
                    # shell variables.
                    self.__dict__[key] = os.path.expandvars(value)  # value

                except TypeError:
                    # if value is an int, expandvars() will fail; if
                    # expandvars() fails, just use the raw value
                    self.__dict__[key] = value

    def __getitem__(self, key):
        ''' Provides dict-style access to attributes. '''

        return getattr(self, key)

    def __repr__(self):
        return str(self.__dict__)

    def copy(self):
        ''' WARNING: this returns a DICT!! '''

        return {
            key: getattr(self, key) for key in self.keys_to_dump
        }

    def items(self):

        # assert lprint_caller_name()

        for key in self.keys_to_dump:
            yield key, getattr(self, key)

    def __setattr__(self, prop, val):
        ''' Record new attributes for future YAML dumping. '''

        # assert lprint_caller_name()

        super().__setattr__(prop, val)

        if prop not in self.keys_to_dump:
            # avoid duplicates when re-assigning attributes,
            # like in obj.mylist += ['item']
            self.keys_to_dump.append(prop)

    def __delattr__(self, prop):
        ''' Remove attributes from future YAML dumps. '''

        # assert lprint_caller_name()

        super().__delattr__(prop)
        self.keys_to_dump.remove(prop)

    def __getattr__(self, name):

        # assert lprint_caller_name()

        if name in self.__dict__:
            return self.name

        else:
            if self.return_defaults:
                # If this object has default mode on, then we should
                # simply return None of the requested attribute as
                # a default, if no attribute with that name exists.
                return None

            else:
                raise AttributeError(
                    'No attribute “{0}” on {1}'.format(
                        name, self.__class__.__name__))


class AttributeDictFromYaml(AttributeDict):
    ''' This class is meant to be subclassed.

        .warn:: Suport for `auto_save` is partial and will *never* be
            complete: when you update/modify an attribute *in-place*,
            the instance *cannot* know you dit it. In this case, you
            have to call `:meth:save` yourself.
    '''

    filename = None
    auto_save = True

    def __init__(self, *args, **kwargs):

        assert(self.filename)

        filename = self.filename

        touch_file(filename)

        ydata = yaml.load(open(filename, 'r')) or {}

        super().__init__(ydata, default=True, *args, **kwargs)

        LOGGER.debug('{0} loaded from “{1}”.'.format(
                     self.__class__.__name__, self.filename))

    def __setattr__(self, prop, val):

        # assert lprint_caller_name()
        # assert lprint(prop, val)

        super().__setattr__(prop, val)

        if self.auto_save:
            self.save()

    def __delattr__(self, prop):

        # assert lprint_caller_name()
        # assert lprint(prop, getattr(self, prop))

        super().__delattr__(prop)

        if self.auto_save:
            self.save()

    def save(self):

        # assert lprint_caller_name()

        with open(self.filename, 'w') as f:
            yaml.add_representer(type(self), Representer.represent_dict)
            yaml.add_representer(AttributeDictFromYaml,
                                 Representer.represent_dict)
            yaml.add_representer(AttributeDict, Representer.represent_dict)
            yaml.add_representer(type(None), Representer.represent_none)

            # f.write(yaml.dump(self, default_flow_style=True))
            f.write(yaml.dump(self, default_flow_style=False,
                              width=72, indent=2))

        LOGGER.debug('{0} saved to “{1}”.'.format(
                     self.__class__.__name__, self.filename))


import os
import logging


#
# HEADS UP: do NOT import constants here.
#


LOGGER = logging.getLogger(__name__)

# Application data (eg. /usr/share/bibed/data)
BIBED_DATA_DIR = os.path.join(os.path.realpath(
    os.path.abspath(os.path.dirname(__file__))), 'data')
BIBED_ICONS_DIR = os.path.join(BIBED_DATA_DIR, 'icons')


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

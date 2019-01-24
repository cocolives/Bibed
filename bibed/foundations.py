
import os
import yaml
import inspect
import logging

from yaml.representer import Representer

from bibed.styles import (
    stylize,
    ST_ATTR,
    ST_PATH,
    ST_COMMENT,
)

LOGGER = logging.getLogger(__name__)


# ————————————————————————————————————————————————————————————— Functions


def ltrace_function_name():

    # for frame, filename, line_num, func, source_code,
    # source_index in inspect.stack():
    stack = inspect.stack()

    return '{0} ({1}:{2})'.format(
        stylize(ST_ATTR, stack[2][3] + u'()'),
        stylize(ST_PATH, stack[2][1]),
        stylize(ST_COMMENT, stack[2][2])
    )


def touch_file(filename):
    ''' Create a file (containing a newline) if missing. '''

    # TODO: touch the file if already existing.

    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            f.write('\n')

        if __debug__:
            LOGGER.debug(
                'touch_file(): created “{}”.'.format(filename))


# ———————————————————————————————————————————————————————————————— Classes


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

    def items(self):
        for key in self.keys_to_dump:
            yield key, getattr(self, key)

    def __setattr__(self, prop, val):
        ''' Record new attributes for future YAML dumping. '''
        super().__setattr__(prop, val)

        if prop not in self.keys_to_dump:
            # avoid duplicates when re-assigning attributes,
            # like in obj.mylist += ['item']
            self.keys_to_dump.append(prop)

    def __delattr__(self, prop):
        ''' Remove attributes from future YAML dumps. '''
        super().__delattr__(prop)
        self.keys_to_dump.remove(prop)

    def __getattr__(self, name):

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

        if __debug__:
            LOGGER.debug(
                '{0} loaded from “{1}”.'.format(
                    self.__class__.__name__, self.filename))

    def __setattr__(self, prop, val):

        if __debug__:
            # This should not obstruct the
            # interpreter in normal conditions.
            LOGGER.debug(
                '{0}.__setattr__({1}={2}) was {3}.'.format(
                    self.__class__.__name__, prop, val,
                    getattr(self, prop)))

        super().__setattr__(prop, val)

        if self.auto_save:
            self.save()

    def __delattr__(self, prop):

        if __debug__:
            # This should not obstruct the
            # interpreter in normal conditions.
            LOGGER.debug(
                '{0}.__detattr__({1}) was {2}.'.format(
                    self.__class__.__name__, prop,
                    getattr(self, prop)))

        super().__delattr__(prop)

        if self.auto_save:
            self.save()

    def save(self):

        # print(ltrace_function_name())

        with open(self.filename, 'w') as f:
            yaml.add_representer(type(self), Representer.represent_dict)
            yaml.add_representer(AttributeDictFromYaml,
                                 Representer.represent_dict)
            yaml.add_representer(AttributeDict, Representer.represent_dict)
            yaml.add_representer(type(None), Representer.represent_none)

            f.write(yaml.dump(self, default_flow_style=False))

        if __debug__:
            LOGGER.debug(
                '{0} saved to “{1}”.'.format(
                    self.__class__.__name__, self.filename))


class Singleton(type):
    ''' https://stackoverflow.com/q/6760685/654755 '''

    _instances = {}

    def __call__(cls, *args, **kwargs):

        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton,
                                        cls).__call__(*args, **kwargs)

            if __debug__:
                LOGGER.debug(
                    '__call__ Singleton for {0}.'.format(
                        cls.__name__))

        return cls._instances[cls]


class NoWatchContextManager:
    ''' A simple context manager to temporarily disable inotify watches. '''

    def __init__(self, application, filename):

        self.application = application
        self.filename = filename

    def __enter__(self):
        self.application.inotify_remove_watch(self.filename)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.application.inotify_add_watch(self.filename)

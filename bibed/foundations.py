
import sys
import os
import ctypes
import ctypes.util
import yaml
import inspect
import logging

from yaml.representer import Representer

from bibed.styles import (
    stylize,
    ST_ATTR,
    ST_PATH,
    ST_NAME,
    ST_DEBUG,
    ST_COMMENT,
    ST_VALUE,
    ST_IMPORTANT,
)

LOGGER = logging.getLogger(__name__)


# ————————————————————————————————————————————————————————————— Functions

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
            LOGGER.warning("Setting the process title failed.")


def ldebug(message, *args, **kwargs):
    ''' function meant to be wrapped in an assert call. '''

    LOGGER.debug(message.format(*args, **kwargs))

    return True


def lprint_caller_name(levels=None):
    ''' Print the stack previous level function name (eg. “caller”).

        .. note:: if you want to print current function name (the one where
            the `ltrace_caller_name` call is in), just wrap it in a lamda.

        .. todo:: re-integrate :func:`ltrace_func` from
            :mod:`licorn.foundations.ltrace` to ease debugging.
    '''

    if levels is None:
        levels = [2]

    else:
        levels = [index for index in range(2 + levels, 2, -1)]

    for level in levels:
        lprint_function_name(
            level=level,
            prefix='{}from '.format(
                ' ' * (level - 1)
            )
        )

    # Stay compatible with assert calls
    return True


def lprint_function_name(level=None, prefix=None):
    ''' Print the stack previous level function name (eg. “caller”).

        .. note:: if you want to print current function name (the one where
            the `ltrace_caller_name` call is in), just wrap it in a lamda.

        .. todo:: re-integrate :func:`ltrace_func` from
            :mod:`licorn.foundations.ltrace` to ease debugging.
    '''

    if level is None:
        level = 1

    if prefix is None:
        prefix = ''

    assert int(level)

    # for frame, filename, line_num, func, source_code,
    # source_index in inspect.stack():
    stack = inspect.stack()

    try:
        sys.stderr.write('{0}{1} ({2}:{3})\n'.format(
            prefix,
            stylize(ST_ATTR, stack[level][3] + '()'),
            stylize(ST_PATH, stack[level][1]),
            stylize(ST_COMMENT, stack[level][2])
        ))
    except IndexError:
        sys.stderr.write('{0}{1}\n'.format(
            prefix,
            'no more frame upwards.')
        )

    # Stay compatible with assert calls.
    return True


def ltrace_frame_informations(with_var_info=False, func=repr, full=False, level=None):
    """ Returns informations about the current calling function. """

    if level is None:
        level = 1

    try:
        # for frame, filename, line_num, func, source_code, source_index in inspect.stack():
        stack = inspect.stack()

    except IndexError:
        # we just hit https://github.com/hmarr/django-debug-toolbar-mongo/pull/9
        # because we are called from inside a Jinja2 template.
        return 'stack frame unavailable in runtime-compiled code.'

    # we allow calling with e.g `level = 99` or `level = -1`,
    # for unlimited stack retrieval and display.
    if level >= len(stack) or level < 0:
        # We substract 2 because later we compute `xrange(3, 2 + level)`
        level = len(stack) - 2

    if full:
        def print_var(var):
            try:
                length = ', len={}'.format(stylize(ST_VALUE, len(var)))

            except Exception:
                length = ''

            return '{var} [type={type}, class={klass}{length}]'.format(
                var=stylize(ST_VALUE, func(var)),
                type=stylize(ST_ATTR, type(var).__name__),
                klass=stylize(ST_ATTR, var.__class__.__name__),
                length=length)
    else:
        def print_var(var):
            return func(var)

    # args is a list of the argument
    # names (it may contain nested lists). varargs and keywords are the
    # names of the * and ** arguments or None. locals is the locals
    # dictionary of the given frame.

    if with_var_info:
        # stack[1] is the `ltrace_var()` call
        args, varargs, keywords, flocals = inspect.getargvalues(stack[1][0])

        return '{fargs}{fkwargs} {where}'.format(
            # the *args of the `ltrace_var()` or `lprint()` call.
            # Use `repr()`.
            fargs=', '.join(print_var(value) for value in flocals[varargs])
            if varargs else '',

            # the **kwargs of the `ltrace_var()` or `lprint()` call. Use `repr()`
            fkwargs=', '.join(
                '{key}={val}'.format(
                    key=stylize(ST_NAME, key), val=print_var(value))
                for key, value in flocals[keywords].items()
            )
            if keywords else '',

            where=',\n'.join(
                stylize(ST_DEBUG, 'in {0} ({1}:{2})'.format(
                    # the name of the surrounding function
                    stack[lev][3],
                    # the filename of the surrounding function
                    stack[lev][1],
                    # the line number from the ltrace call
                    # (not the def of the calling function)
                    stack[lev][2]
                )
                    # we can trace the call from outside the original caller if needed.
                ) for lev in range(2, 2 + level)
            )
        )
    else:
        # NOTE: we use stack[2], because:
        #    - stack[0] is the current function 'ltrace_frame_informations()' call
        #    - stack[1] is the 'ltrace()' or 'warn_exc()' call
        #    - stack[2] is logically the calling function,
        #        the real one we want informations from.
        args, varargs, keywords, flocals = inspect.getargvalues(stack[2][0])

        return '{func_name}({fargs}{comma_f}{fvarargs}{comma_v}{fkwargs}) in {filename}:{lineno}{fromcall}'.format(
            # name of the calling function
            func_name=stylize(ST_ATTR, stack[2][3]),

            # NOTE: we use repr() because in `__init__()`
            # methods `str()` might crash because the objects
            # are not yet fully initialized and can miss
            # attributes used in their `__str__()`.
            fargs=', '.join('{0}={1}'.format(
                stylize(ST_NAME, var_name),
                print_var(flocals[var_name])
            ) for var_name in args),

            # just a comma, to separate the first named args from *a and **kw.
            comma_f=', ' if (args and (varargs != [] or keywords != [])) else '',

            # the *args. Use `repr()`
            fvarargs=', '.join(
                print_var(value)
                for value in flocals[varargs]
            ) if varargs else '',

            # just a comma, to separate *a and **kw.
            comma_v=', ' if (varargs != [] and keywords != []) else '',

            # the **kwargs. use `repr()`
            fkwargs=', '.join(
                '{0}={1}'.format(
                    stylize(ST_NAME, key),
                    print_var(value)
                )
                for key, value in flocals[keywords].items()
            ) if keywords else '',

            # filename of called function
            filename=stylize(ST_PATH, stack[2][1]),
            # line number of called function
            lineno=stylize(ST_COMMENT, stack[2][2]),

            fromcall=(
                '\n\t\tfrom {}'.format('\n\t\tfrom '.join(
                    '{0}:{1}'.format(
                        stylize(ST_PATH, stack[lev][1]),
                        stylize(ST_COMMENT, stack[lev][2])
                    ) for lev in range(3, 2 + level)
                ))
            ) if level > 1 else ''
        )


def lprint(*args, **kwargs):
    """ Print things (variables) with colors in development phases.

        Use `assert lprint(var1, dict2, klass3, …)` calls.

        Use of this function helps removing these calls, because they advertise themselves from where they are called in the code. If you let them, just
        run with :program:`python -O` to avoid the overhead.
    """

    sys.stderr.write('{0} {1}\n'.format(
        stylize(ST_IMPORTANT, '>>'),
        ltrace_frame_informations(with_var_info=True, func=str, full=True))
    )

    # stay compatible with assert, as all other `ltrace` functions.
    return True


def touch_file(filename):
    ''' Create a file (containing a newline) if missing. '''

    # TODO: touch the file if already existing.

    # assert lprint_caller_name()
    # assert lprint(filename)

    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            f.write('\n')

        assert ldebug('touch_file(): created “{}”.', filename)


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

        assert ldebug('{0} loaded from “{1}”.',
                      self.__class__.__name__, self.filename)

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

        # assert ldebug(
        #     '{0} saved to “{1}”.', self.__class__.__name__, self.filename)


class Singleton(type):
    ''' https://stackoverflow.com/q/6760685/654755 '''

    _instances = {}

    def __call__(cls, *args, **kwargs):

        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton,
                                        cls).__call__(*args, **kwargs)

            # assert ldebug('__call__ Singleton for {0}.', cls.__name__)

        return cls._instances[cls]

import sys
import inspect

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


def ldebug(message, *args, **kwargs):
    ''' function meant to be wrapped in an assert call. '''

    print(message.format(*args, **kwargs))

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


import logging
import webbrowser
import subprocess

from bibed.exceptions import ActionError

from bibed.ltrace import (  # NOQA
    ldebug, lprint,
    lprint_caller_name,
    lprint_function_name,
)

from bibed.foundations import (
    is_osx, is_windows,
)

LOGGER = logging.getLogger(__name__)


# ————————————————————————————————————————————————————————————— Functions

def open_urls_in_web_browser(urls):

    for url in urls:
        webbrowser.open_new_tab(url)


def open_with_system_launcher(filenames):

    if is_osx():
        base_command = ['open']

    elif is_windows():
        base_command = ['start']

    else:
        # Linux
        base_command = ['xdg-open']

    for filename in filenames:
        if filename.startswith(':') and filename.lower().endswith(':pdf'):
            # get rid of older filenames like “:/home/olive/myfile.pdf:PDF”
            filename = filename[1:-4]

        command = base_command + [filename]

        try:
            # This will raise an exception if any error is encountered.
            subprocess.check_call(command)

        except Exception:
            raise ActionError(' '.join(command))


# ———————————————————————————————————————————————————————————————— Classes

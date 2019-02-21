
import os
import random
import logging

from bibed.constants import (
    BIBED_DATA_DIR,
    BIBED_ICONS_DIR,
    BIBED_BACKGROUNDS_DIR,
    MAIN_TREEVIEW_CSS,
    ENTRY_COLORS,
)

from bibed.preferences import gpod
from bibed.entry import BibedEntry
from bibed.gtk import Gtk, Gdk, Gio


LOGGER = logging.getLogger(__name__)


class GtkCssAwareMixin:
    ''' Handles CSS related methods & properties, and implements random
        background cycling. '''

    def setup_resources_and_css(self):
        ''' Must called as soon as possible, anyhere in the window/application initialization phase. '''

        if not Gtk.IconSize.from_name('BIBED_BIG'):
            Gtk.IconSize.register('BIBED_BIG', 96, 96)
            Gtk.IconSize.register('BIBED_SMALL', 32, 32)

        self.__css_filename = os.path.join(BIBED_DATA_DIR, 'style.css')

        with open(self.__css_filename) as css_file:
            self.__css_data_string = css_file.read()

        try:
            self.set_resource_base_path(BIBED_DATA_DIR)

        except AttributeError:
            # This works only for Gtk.Application*
            pass

        default_screen = Gdk.Screen.get_default()

        # could also be .icon_theme_get_default()
        self.icon_theme = Gtk.IconTheme.get_for_screen(default_screen)

        self.icon_theme.add_resource_path(BIBED_DATA_DIR)

        # Get an icon path.
        # icon_info = icon_theme.lookup_icon("my-icon-name", 48, 0)
        # print icon_info.get_filename()

        self.css_provider = Gtk.CssProvider()

        # Loads the first background.
        self.reload_css_provider_data()

        self.style_context = Gtk.StyleContext()

        self.style_context.add_provider_for_screen(
            default_screen,
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER)

    @property
    def css_data(self):

        css_data_string = self.__css_data_string[:] + MAIN_TREEVIEW_CSS

        css_data_string = css_data_string.replace(
            '{{theme_{}}}'.format(self.__css_theme_disabled), '_disabled')

        css_data_string = css_data_string.replace(
            '{{theme_{}}}'.format(self.__css_theme), '')

        if gpod('use_treeview_background'):
            background_filename = \
                self.get_random_background(self.__css_theme)
            background_position = None
            background_size = None

            if '-contain' in background_filename:
                background_size = 'contain'

            elif '-cover' in background_filename:
                background_size = 'cover'

            if background_size is None:
                background_size = 'cover'

            for vertical_position in ('top', 'bottom', ):
                for horizontal_position in ('left', 'right', ):
                    if vertical_position in background_filename \
                            and horizontal_position in background_filename:
                        background_position = '{} {}'.format(
                            horizontal_position, vertical_position)

            if background_position is None:
                background_position = 'left top'

            # Enable background use in CSS.
            css_data_string = css_data_string.replace(
                '{use_background}', '')

            css_data_string = css_data_string.replace(
                '{background_filename}', background_filename)
            css_data_string = css_data_string.replace(
                '{background_position}', background_position)
            css_data_string = css_data_string.replace(
                '{background_size}', background_size)

        else:
            css_data_string = css_data_string.replace(
                '{use_background}', '_disabled')

        # print('CSS DATA\n', css_data_string)

        return css_data_string

    def get_random_background(self, theme):

        for root, dirs, files in os.walk(
                os.path.join(BIBED_BACKGROUNDS_DIR, theme)):
            return os.path.join(BIBED_BACKGROUNDS_DIR,
                                theme, random.choice(files))

    def reload_css_provider_data(self):
        ''' The method called from action, button or keyboard shortcut.

            This method calls necessary things to change / cycle background.
        '''

        if self.is_dark_theme():
            self.__css_theme = 'dark'
            self.__css_theme_disabled = 'light'

        else:
            self.__css_theme = 'light'
            self.__css_theme_disabled = 'dark'

        BibedEntry.COLORS = ENTRY_COLORS[self.__css_theme]

        # self.icon_theme.add_resource_path(BIBED_ICONS_DIR)

        icons_enabled = os.path.join(BIBED_ICONS_DIR, self.__css_theme)
        icons_disabled = os.path.join(BIBED_ICONS_DIR, self.__css_theme_disabled)

        search_path = self.icon_theme.get_search_path()

        try:
            search_path.remove(icons_disabled)

        except ValueError:
            pass

        search_path.insert(0, icons_enabled)

        self.icon_theme.set_search_path(search_path)

        self.icon_theme.rescan_if_needed()

        print(self.icon_theme.get_search_path())

        self.css_provider.load_from_data(bytes(self.css_data.encode('utf-8')))

    def is_dark_theme(self):

        try:
            settings = Gio.Settings("org.gnome.desktop.interface")
            theme_name = settings.get_string('gtk-theme')

        except Exception:
            LOGGER.exception('Could not determine theme name.')

            # Still allow user to choose between dark and light themes.
            return gpod('force_dark_theme')

        return 'dark' in theme_name.lower()

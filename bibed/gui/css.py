
import os
import random

from bibed.constants import (
    BIBED_DATA_DIR,
    BIBED_ICONS_DIR,
    BIBED_BACKGROUNDS_DIR,
    MAIN_TREEVIEW_CSS,
)

from bibed.preferences import gpod
from bibed.gtk import Gtk, Gdk


class GtkCssAwareMixin:
    ''' Handles CSS related methods & properties, and implements random
        background cycling. '''

    def setup_resources_and_css(self):
        ''' Must called as soon as possible, anyhere in the window/application initialization phase. '''

        self.__css_filename = os.path.join(BIBED_DATA_DIR, 'style.css')

        try:
            self.set_resource_base_path(BIBED_DATA_DIR)

        except AttributeError:
            # This works only for Gtk.Application*
            pass

        default_screen = Gdk.Screen.get_default()

        # could also be .icon_theme_get_default()
        self.icon_theme = Gtk.IconTheme.get_for_screen(default_screen)

        self.icon_theme.add_resource_path(BIBED_DATA_DIR)
        self.icon_theme.add_resource_path(BIBED_ICONS_DIR)

        self.icon_theme.set_search_path(
            [BIBED_ICONS_DIR] + self.icon_theme.get_search_path())

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

        with open(self.__css_filename) as css_file:
            self.__css_data_string = css_file.read()

        if gpod('use_treeview_background'):
            background_filename = self.get_random_background()
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

            css_data_string = self.__css_data_string[:] + MAIN_TREEVIEW_CSS

            css_data_string = css_data_string.replace(
                '{background_filename}', background_filename)
            css_data_string = css_data_string.replace(
                '{background_position}', background_position)
            css_data_string = css_data_string.replace(
                '{background_size}', background_size)

            return css_data_string

        return self.__css_data_string

    def get_random_background(self):

        for root, dirs, files in os.walk(BIBED_BACKGROUNDS_DIR):
            return os.path.join(BIBED_BACKGROUNDS_DIR, random.choice(files))

    def reload_css_provider_data(self):
        ''' The method called from action, button or keyboard shortcut.

            This method calls necessary things to change / cycle background.
        '''

        self.css_provider.load_from_data(bytes(self.css_data.encode('utf-8')))

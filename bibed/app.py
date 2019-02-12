
import os
import logging
import random
import time

from bibed.ltrace import (  # NOQA
    ldebug, lprint,
    lprint_caller_name,
    lprint_function_name,
)

from bibed.constants import (
    APP_ID,
    APP_NAME,
    APP_VERSION,
    APP_MENU_XML,
    BIBED_DATA_DIR,
    BIBED_ICONS_DIR,
    BIBED_BACKGROUNDS_DIR,
    BibAttrs,
    SEARCH_SPECIALS,
    BIBTEXPARSER_VERSION,
    MAIN_TREEVIEW_CSS,
)

from bibed.foundations import (
    touch_file,
    set_process_title,
)

from bibed.strings import (
    to_lower_if_not_none,
    seconds_to_string,
)

# Import Gtk before preferences, to initialize GI.
from bibed.gtk import Gio, GLib, Gtk, Gdk, Notify

from bibed.preferences import preferences, memories, gpod

from bibed.store import (
    BibedDataStore,
    BibedFileStore,
    AlreadyLoadedException,
)

from bibed.gui.window import BibedWindow


LOGGER = logging.getLogger(__name__)

# This fixes the name displayed in the GNOME Menu bar.
# Without this, the name is 'Bibed.py'.
GLib.set_prgname(APP_NAME)

set_process_title(APP_NAME)
# set after main loop has started (gtk seems to reset it)
GLib.idle_add(set_process_title, APP_NAME)

# Not sure what this is for, but it seems important in
# Gtk/GLib documentation.
GLib.set_application_name(APP_NAME)


class BibEdApplication(Gtk.Application):

    def __init__(self, *args, **kwargs):

        self.splash = kwargs.pop('splash')
        self.time_start = kwargs.pop('time_start')
        self.logging_handlers = kwargs.pop('logging_handlers')

        LOGGER.info('Starting application.')

        super().__init__(*args, application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                         **kwargs)

        self.add_main_option(
            "test", ord("t"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Command line test", None)

        # TODO: If there is a resource located at “gtk/help-overlay.ui”
        # which defines a Gtk.ShortcutsWindow with ID “help_overlay” […].
        # To create a menu item that displays the shortcuts window,
        # associate the item with the action win.show-help-overlay.

        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.window = None

        self.setup_data_store()

    # ——————————————————————————————————————————————————————————— setup methods

    @property
    def css_data(self):

        with open(os.path.join(BIBED_DATA_DIR, 'style.css')) as css_file:
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

    def setup_resources_and_css(self):

        self.set_resource_base_path(BIBED_DATA_DIR)

        default_screen = Gdk.Screen.get_default()

        # could also be .icon_theme_get_default()
        self.icon_theme = Gtk.IconTheme.get_for_screen(default_screen)
        self.icon_theme.add_resource_path(os.path.join(BIBED_ICONS_DIR))

        # Get an icon path.
        # icon_info = icon_theme.lookup_icon("my-icon-name", 48, 0)
        # print icon_info.get_filename()

        self.css_provider = Gtk.CssProvider()

        self.reload_css_provider_data()

        self.style_context = Gtk.StyleContext()
        self.style_context.add_provider_for_screen(
            default_screen,
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def reload_css_provider_data(self):

        # This will fill the CSS string with a random background on the fly.
        self.css_provider.load_from_data(bytes(self.css_data.encode('utf-8')))

    def setup_actions(self):

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)

        # TODO: take back window keypresses here.
        # Use https://lazka.github.io/pgi-docs/Gtk-3.0/classes/Application.html#Gtk.Application.add_accelerator  # NOQA

        # TODO: implement a shortcuts window.
        # from https://lazka.github.io/pgi-docs/Gtk-3.0/classes/ShortcutsWindow.html#Gtk.ShortcutsWindow  # NOQA
        pass

    def setup_app_menu(self):

        # TODO: move menus to gtk/menus.ui for automatic load.
        #       and gtk/menus-common.ui
        #
        # See “Automatic Resources” at https://lazka.github.io/pgi-docs/Gtk-3.0/classes/Application.html#Gtk.Application  # NOQA

        builder = Gtk.Builder.new_from_string(APP_MENU_XML, -1)
        self.set_app_menu(builder.get_object("app-menu"))

    def setup_data_store(self):

        # Stores open files (user / system / other)
        self.files = BibedFileStore()

        # Stores All BIB entries.
        self.data = BibedDataStore(files_store=self.files)

        # This must be done after the data store has loaded.
        self.files.load_system_files()

        # Keep the filter data sortable along the way.
        self.filter = self.data.filter_new()
        # self.filter = Gtk.TreeModelFilter(self.data)
        self.sorter = Gtk.TreeModelSort(self.filter)
        self.filter.set_visible_func(self.data_filter_method)

    def close_splash(self):

        self.splash.destroy()
        self.splash = None

    # ——————————————————————————————————————————————————————— data store filter

    def data_filter_method(self, model, iter, data):

        # a local reference for faster access.
        matched_files = self.window.matched_files

        try:
            filter_text = self.window.search.get_text()

        except AttributeError:
            # The window is not yet constructed
            return True

        row = model[iter]

        try:
            selected_filenames = self.window.get_selected_filenames()

        except TypeError:
            # The window is not yet constructed.
            return True

        else:
            if not selected_filenames:
                # No data should match when no file is selected.
                return False

            elif row[BibAttrs.FILENAME] not in selected_filenames:
                # The current row is not part of displayed
                # files. No need to go further.
                return False

        if filter_text is None:
            matched_files.add(row[BibAttrs.FILENAME])
            return True

        filter_text = filter_text.strip().lower()

        if not filter_text:
            return True

        words = filter_text.split()

        specials = []
        full_text = []

        for word in words:
            if ':' in word:
                specials.append([x.lower() for x in word.split(':')])
            else:
                full_text.append(word)

        for key, val in specials:
            for char, index, label in SEARCH_SPECIALS:
                if key == char:
                    if val not in row[index].lower():
                        return False

        # TODO: unaccented / delocalized search.

        model_full_text_data = [
            to_lower_if_not_none(row[BibAttrs.AUTHOR]),
            to_lower_if_not_none(row[BibAttrs.TITLE]),
            to_lower_if_not_none(row[BibAttrs.JOURNAL]),
            to_lower_if_not_none(row[BibAttrs.SUBTITLE]),
            to_lower_if_not_none(row[BibAttrs.COMMENT]),
            # NO abstract yet in data_store.
            # to_lower_if_not_none(model[iter][BibAttrs.ABSTRACT])
        ]

        for word in full_text:
            if word not in ' '.join(model_full_text_data):
                return False

        matched_files.add(row[BibAttrs.FILENAME])
        return True

    # ———————————————————————————————————————————————————————————— do “actions”

    def do_startup(self):
        Gtk.Application.do_startup(self)

        self.setup_resources_and_css()

        self.setup_actions()
        self.setup_app_menu()

    def do_notification(self, message):

        notification = Notify.Notification.new('Bibed', message)
        # notification.set_timeout(Notify.EXPIRES_NEVER)
        # notification.add_action('quit', 'Quit', notification_callback)
        notification.show()

    def do_activate(self):

        # For GUI-setup-order related reasons,
        # we need to delay some things.
        search_grab_focus = False
        databases_to_select = []
        filenames_to_select = []

        # We only allow a single window and raise any existing ones
        if not self.window:
            Notify.init(APP_NAME)

            # Windows are associated with the application
            # when the last one is closed the application shuts down
            self.window = BibedWindow(title='Main Window', application=self)
            self.window.show_all()

            if preferences.remember_open_files:

                if memories.open_files:

                    # 1: search_text needs to be loaded first, else it gets
                    # wiped when file_combo is updated with re-loaded files.
                    # 2: don't load it if there are no open_files.
                    # 3: dont call do_filter_data_store(), it will be called
                    # by on_files_combo_changed() when files are added.
                    if memories.search_text is not None:
                        self.window.search.set_text(memories.search_text)
                        search_grab_focus = True

                    # Idem, same problem.
                    if memories.selected_filenames is not None:
                        filenames_to_select = memories.selected_filenames

                    else:
                        filenames_to_select = memories.open_files.copy()

                    # Then, load all previously opened files.
                    # Get a copy to avoid the set being changed while we load,
                    # because in some corner cases the live “re-ordering”
                    # makes a file loaded two times.

                    with self.window.block_signals():
                        # We need to block signals and let win.do_activate()
                        # Update everything, else some on_*_changed() signals
                        # are not fired. Don't know if it's a Gtk or pgi bug.

                        for filename in memories.open_files.copy():
                            try:
                                database = self.open_file(filename,
                                                          select=False)

                            except (IOError, OSError):
                                # TODO: move this into store ?
                                memories.remove_open_file(filename)

                            else:
                                if filename in filenames_to_select:
                                    # we have to convert filenames to databases
                                    # because all of this seems to happen too
                                    # fast for store to be ready to return
                                    # .get_database() results before the end
                                    # of the current method.
                                    databases_to_select.append(database)

        if sorted(filenames_to_select) != sorted([x.filename for x in databases_to_select]):
            # Most probably a system file was selected before closing.
            # Try to get it again.

            for filename in filenames_to_select:
                for system_database in self.files.system_databases:
                    if filename == system_database.filename:
                        databases_to_select.append(system_database)

        if databases_to_select:
            self.window.set_selected_databases(databases_to_select)

            # Selecting a system database is the only case that doesn't
            # trigger a full window / treeview update. Fake it.
            if len(tuple(self.files.selected_system_databases)):
                self.window.on_selected_files_changed()
        else:
            if not self.files.num_user:
                # No database. Trigger a treeview filter
                # anyway to hide the system entries if any.
                self.window.on_selected_files_changed()
                self.window.do_activate()

            else:
                self.window.files_popover.listbox.select_all()
                # self.window.do_activate()

        if search_grab_focus:
            self.window.searchbar.set_search_mode(True)
            self.window.search.grab_focus()

        # TODO: splash doesn't work.
        self.close_splash()

        LOGGER.info('Startup time (including session restore): {}'.format(
            seconds_to_string(time.time() - self.time_start)))

        self.window.present()

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()

        # convert GVariantDict -> GVariant -> dict
        options = options.end().unpack()

        if 'test' in options:
            LOGGER.info("Test argument received: %s" % options['test'])

        self.activate()
        return 0

    def run(self, *args, **kwargs):

        try:
            super().run(*args, **kwargs)

        except KeyboardInterrupt:
            LOGGER.warning('Interrupted, terminating properly…')
            self.on_quit(None, None)

    # ———————————————————————————————————————————— higher level file operations
    # TODO: move them to main window?

    def create_file(self, filename):
        ''' Create a new BIB file, then open it in the application. '''

        # assert lprint_function_name()

        touch_file(filename)

        self.open_file(filename)

    def open_file(self, filename, select=True, recompute=True):
        ''' Add a file to the application. '''

        # assert lprint_function_name()
        # assert lprint(filename, recompute)

        # Be sure we keep a consistent path across all application.
        filename = os.path.realpath(os.path.abspath(filename))

        try:
            # Note: via events, this will update the window title.
            database = self.files.load(filename, recompute=recompute)

        except AlreadyLoadedException:
            self.do_notification('“{}” already loaded.'.format(filename))
            # TODO: Select / Focus the file.
            return

        except Exception as e:
            message = 'Cannot load file “{0}”: {1}'.format(filename, e)
            LOGGER.exception(message)

            self.window.do_status_change(message)
            return

        if select:
            self.window.set_selected_databases([database])

        # Needed for correct session reload.
        return database

    def reload_files(self, message=None):

        # assert lprint_function_name()
        # assert lprint(message)

        for filename in self.files.get_open_filenames():
            self.reload_file(filename)

        if message:
            self.window.do_status_change(message)

    def reload_file(self, filename, message=None):

        # assert lprint_function_name()
        # assert lprint(filename, message)

        if self.files.reload(filename):
            if message:
                self.window.do_status_change(message)

    def close_file(self, filename, save_before=True, recompute=True, remember_close=True):
        ''' Close a file and impact changes. '''

        # assert lprint_function_name()

        self.files.close(filename,
                         save_before=save_before,
                         recompute=recompute,
                         remember_close=remember_close)

    # ———————————————————————————————————————————————————————————— on “actions”

    def on_about(self, action, param):

        # assert lprint_function_name()

        about_dialog = Gtk.AboutDialog(
            transient_for=self.window, modal=True)

        about_dialog.set_program_name(APP_NAME)
        about_dialog.set_version(APP_VERSION)
        about_dialog.set_logo_icon_name('gnome-contacts.png')
        # os.path.join(BIBED_ICONS_DIR, 'gnome-contacts.png'))

        about_dialog.set_copyright('(c) Collectif Cocoliv.es')

        comments = (
            'Bibliographic assistance libre software\n\n'
            'GTK v{}.{}.{}\n'
            'bibtexparser v{}'.format(
                Gtk.get_major_version(),
                Gtk.get_minor_version(),
                Gtk.get_micro_version(),
                BIBTEXPARSER_VERSION,
            )
        )

        if gpod('use_sentry'):
            try:
                import sentry_sdk

            except Exception:
                LOGGER.error('Unable to import sentry SDK.')

            else:
                last_event = sentry_sdk.last_event_id()

                comments += (
                    '\nSentry SDK v{sdk_vers}, reporting to\n{dsn}\n'
                    '(see {website} for details)'
                    '{last}'.format(
                        sdk_vers=sentry_sdk.VERSION,
                        dsn=gpod('sentry_dsn'),
                        website=gpod('sentry_url'),
                        last='<big>Last event ID: {}</big>'.format(last_event)
                        if last_event else ''
                    )
                )

        about_dialog.set_comments(comments)

        about_dialog.set_website('https://cocoliv.es/library/bibed')
        about_dialog.set_website_label('Site web de Bibed')
        about_dialog.set_license_type(Gtk.License.GPL_3_0)

        about_dialog.set_authors([
            'Olivier Cortès <olive@cocoliv.es>',
            'Collectif Cocoliv.es <contact@cocoliv.es>',
        ])
        about_dialog.set_documenters([
            'Olivier Cortès <olive@cocoliv.es>',
        ])
        about_dialog.set_artists([
            'Corinne Carnevali <coco@cocoliv.es>',
        ])
        about_dialog.set_translator_credits(
            'Olivier Cortès <olive@cocoliv.es>'
        )

        # add_credit_section(section_name, people)
        # https://lazka.github.io/pgi-docs/Gtk-3.0/classes/AboutDialog.html#Gtk.AboutDialog.add_credit_section

        about_dialog.present()

    def on_quit(self, action, param):

        # Block signals, else memories.combo_filename will
        # finish empty When last file has been closed.
        self.window.block_signals()

        # This will close system files too.
        self.files.close_all(

            # Save is done along-the-way at each user action that needs it.
            save_before=False,
            recompute=False,

            # This will allow automatic reopen on next launch.
            remember_close=False,
        )

        self.quit()

        LOGGER.info(
            'Terminating application; ran {}.'.format(
                seconds_to_string(time.time() - self.time_start)))

        for handler in self.logging_handlers:
            handler.close()

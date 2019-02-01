
import os
import logging

from collections import OrderedDict

from bibed.constants import (
    APP_ID,
    APP_NAME,
    APP_VERSION,
    APP_MENU_XML,
    BIBED_DATA_DIR,
    BIBED_ICONS_DIR,
    BibAttrs,
    BIBTEXPARSER_VERSION,
)

from bibed.foundations import (
    lprint,
    lprint_function_name,
    set_process_title,
    touch_file,
)

# Import Gtk before preferences, to initialize GI.
from bibed.gui.gtk import Gio, GLib, Gtk, Gdk, Notify

from bibed.utils import to_lower_if_not_none
from bibed.preferences import preferences, memories
from bibed.store import (
    BibedDataStore,
    BibedFileStore,
    AlreadyLoadedException,
)

from bibed.gui.window import BibEdWindow


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
        self.files = OrderedDict()

    # ——————————————————————————————————————————————————————————— setup methods

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
        self.css_provider.load_from_path(
            os.path.join(BIBED_DATA_DIR, 'style.css'))

        self.style_context = Gtk.StyleContext()
        self.style_context.add_provider_for_screen(
            default_screen,
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER)

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

        # Stores All BIB entries.
        self.data = BibedDataStore()

        # Stores open files (user / system / other)
        self.files = BibedFileStore(self.data)

        # Keep the filter data sortable along the way.
        self.filter = self.data.filter_new()
        # self.filter = Gtk.TreeModelFilter(self.data)
        self.sorter = Gtk.TreeModelSort(self.filter)
        self.filter.set_visible_func(self.filter_method)

    # ——————————————————————————————————————————————————————— data store filter

    def filter_method(self, model, iter, data):

        try:
            filter_text = self.window.search.get_text()

        except AttributeError:
            # The window is not yet constructed
            return True

        store_entry = model[iter]

        try:
            filter_file = self.window.get_selected_filename()

        except TypeError:
            # The window is not yet constructed.
            return True

        else:
            # TODO: translate 'All'
            if filter_file != 'All':
                if store_entry[BibAttrs.FILENAME] != filter_file:
                    # The current row is not part of displayed
                    # filename. No need to go further.
                    return False

        if filter_text is None:
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
            if key == 't':  # TYPE
                if val not in store_entry[BibAttrs.TYPE].lower():
                    return False

            if key == 'k':  # (bib) KEY
                if val not in store_entry[BibAttrs.KEY].lower():
                    return False

            if key == 'j':
                if val not in store_entry[BibAttrs.JOURNAL].lower():
                    return False

            if key == 'y':
                if int(val) != int(store_entry[BibAttrs.YEAR]):
                    return False

        # TODO: unaccented / delocalized search.

        model_full_text_data = [
            to_lower_if_not_none(store_entry[BibAttrs.AUTHOR]),
            to_lower_if_not_none(store_entry[BibAttrs.TITLE]),
            to_lower_if_not_none(store_entry[BibAttrs.JOURNAL]),
            to_lower_if_not_none(store_entry[BibAttrs.SUBTITLE]),
            to_lower_if_not_none(store_entry[BibAttrs.COMMENT]),
            # NO abstract yet in data_store.
            # to_lower_if_not_none(model[iter][BibAttrs.ABSTRACT])
        ]

        for word in full_text:
            if word not in ' '.join(model_full_text_data):
                return False

        return True

    # ———————————————————————————————————————————————————————————— do “actions”

    def do_startup(self):
        Gtk.Application.do_startup(self)

        self.setup_resources_and_css()
        self.setup_actions()
        self.setup_app_menu()
        self.setup_data_store()

    def do_notification(self, message):

        notification = Notify.Notification.new('Bibed', message)
        # notification.set_timeout(Notify.EXPIRES_NEVER)
        # notification.add_action('quit', 'Quit', notification_callback)
        notification.show()

    def do_activate(self):

        # For GUI-setup-order related reasons,
        # we need to delay some things.
        search_grab_focus = False
        combo_set_active = None

        # We only allow a single window and raise any existing ones
        if not self.window:
            Notify.init(APP_NAME)

            # Windows are associated with the application
            # when the last one is closed the application shuts down
            self.window = BibEdWindow(title='Main Window', application=self)
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
                    if memories.combo_filename is not None:
                        combo_set_active = memories.combo_filename

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
                                self.open_file(filename)

                            except (IOError, OSError):
                                memories.remove_open_file(filename)

        # make interface consistent with data.
        self.window.do_activate()

        if combo_set_active:
            for row in self.window.filtered_files:
                if row[0] == combo_set_active:
                    # assert lprint('ACTIVATE', combo_set_active, len(self.window.filtered_files))
                    self.window.cmb_files.set_active_iter(row.iter)
                    break

        if search_grab_focus:
            self.window.search.grab_focus()

        self.window.present()

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()

        # convert GVariantDict -> GVariant -> dict
        options = options.end().unpack()

        if 'test' in options:
            LOGGER.info("Test argument received: %s" % options['test'])

        self.activate()
        return 0

    # ———————————————————————————————————————————— higher level file operations
    # TODO: move them to main window?

    def create_file(self, filename):
        ''' Create a new BIB file, then open it in the application. '''

        # assert lprint_function_name()

        touch_file(filename)

        self.open_file(filename)

    def open_file(self, filename, recompute=True):
        ''' Add a file to the application. '''

        # assert lprint_function_name()
        # assert lprint(filename, recompute)

        # Be sure we keep a consistent path across all application.
        filename = os.path.realpath(os.path.abspath(filename))

        try:
            # Note: via events, this will update the window title.
            self.files.load(filename, recompute=recompute)

        except AlreadyLoadedException:
            self.do_notification('“{}” already loaded.'.format(filename))
            # TODO: Select / Focus the file.
            return

        except Exception as e:
            message = 'Cannot load file “{0}”: {1}'.format(filename, e)
            LOGGER.exception(message)

            self.window.do_status_change(message)
            return

        if len(self.files) > 1:
            # Now that we have more than one file,
            # make active and select 'All' by default.
            self.window.cmb_files.set_sensitive(True)

        self.window.cmb_files.set_active(0)

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
            self.window.do_status_change(message)

    def close_file(self, filename, save_before=True, recompute=True, remember_close=True):
        ''' Close a file and impact changes. '''

        # assert lprint_function_name()

        self.files.close(filename,
                         save_before=save_before,
                         recompute=recompute,
                         remember_close=remember_close)

        if len(self.files) < 2:
            # Now that we have more than one file,
            # make active and select 'All' by default.
            self.window.cmb_files.set_active(0)
            self.window.cmb_files.set_sensitive(False)

        else:
            self.window.cmb_files.set_active(0)

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
        about_dialog.set_comments(
            'Bibliographic assistance libre software\n\n'
            'GTK v{}.{}.{}\n'
            'bibtexparser v{}'.format(
                Gtk.get_major_version(),
                Gtk.get_minor_version(),
                Gtk.get_micro_version(),
                BIBTEXPARSER_VERSION,
            )
        )

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
            save_before=True,
            recompute=False,

            # This will allow automatic reopen on next launch.
            remember_close=False,
        )

        LOGGER.info('Terminating application.')
        self.quit()


import os
import logging
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
    BibAttrs,
    SEARCH_SPECIALS,
    BIBTEXPARSER_VERSION,
)

from bibed.decorators import wait_for_queued_events
from bibed.foundations import Anything
from bibed.system import set_program_name_global, touch_file
from bibed.strings import to_lower_if_not_none
from bibed.dtu import seconds_to_string
from bibed.locale import _, NO_

# Import Gtk before preferences, to initialize GI.
from bibed.gtk import Gio, Gtk, Gdk, Notify
from bibed.controllers import controllers
from bibed.daemon import BibedDaemonMixin
from bibed.preferences import preferences, memories, gpod

from bibed.store import (
    BibedDataStore,
    AlreadyLoadedException,
)

from bibed.gui.css import GtkCssAwareMixin

LOGGER = logging.getLogger(__name__)

set_program_name_global(APP_NAME)


class BibedApplication(Gtk.Application, GtkCssAwareMixin, BibedDaemonMixin):

    def __init__(self, *args, **kwargs):

        self.splash = kwargs.pop('splash')
        self.time_start = kwargs.pop('time_start')
        self.logging_handlers = kwargs.pop('logging_handlers')

        controllers.application = self

        LOGGER.info('Starting application.')

        super().__init__(*args, application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                         **kwargs)

        # from BibedDaemonMixin
        self.daemon_setup()

        # TODO: If there is a resource located at “gtk/help-overlay.ui”
        # which defines a Gtk.ShortcutsWindow with ID “help_overlay” […].
        # To create a menu item that displays the shortcuts window,
        # associate the item with the action win.show-help-overlay.

        controllers.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        self.window = None

        self.setup_data_store()

    # ——————————————————————————————————————————————————————————— setup methods

    def setup_actions(self):

        action = Gio.SimpleAction.new('about', None)
        action.connect('activate', self.on_about)
        self.add_action(action)

        self.is_quitting = False

        action = Gio.SimpleAction.new('quit', None)
        action.connect('activate', self.on_quit)
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

        # TODO: externalize app menu in a file for translations.
        builder = Gtk.Builder.new_from_string(APP_MENU_XML, -1)

        self.set_app_menu(builder.get_object('app-menu'))

    def setup_data_store(self):

        # data store for the main window treeview.
        controllers.data = BibedDataStore(controllers=controllers)

        # This must be done after the data store has loaded.
        controllers.files.load_system_files()

        # Keep the filter data sortable along the way.
        self.filter = controllers.data.filter_new()
        # self.filter = Gtk.TreeModelFilter(controllers.data)
        self.sorter = Gtk.TreeModelSort(self.filter)
        self.filter.set_visible_func(self.data_filter_method)

    # ——————————————————————————————————————————————————————— data store filter

    def data_filter_method(self, model, iter, data):

        # a local reference for faster access.
        matched_databases = self.window.matched_databases

        try:
            filter_text = self.window.search.get_text().strip().lower()

        except AttributeError:
            # The window is not yet constructed
            return True

        # Simplify tests.
        if filter_text == '':
            filter_text = None

        row = model[iter]

        try:
            selected_databases_ids = \
                self.window.get_selected_databases(only_ids=True)

        except TypeError:
            # The window is not yet constructed.
            return True

        else:
            if filter_text is not None:
                # If we are searching for text (searchbar is active), there are
                # two special cases: all files selected and no file selected.

                if not selected_databases_ids:
                    # If no file is selected, match all system files.

                    selected_databases_ids = [
                        db.objectid
                        for db in controllers.files.system_databases
                    ]

                elif len(selected_databases_ids) == controllers.files.num_user:
                    # If all files are selected, add system files to the selection.
                    # This is the only way to get a “full” search across all DBs.

                    selected_databases_ids += [
                        db.objectid
                        for db in controllers.files.system_databases
                    ]

            if row[BibAttrs.DBID] not in selected_databases_ids:
                # The current row is not part of selected
                # databases. No need to go further.
                return False

        if filter_text is None:
            matched_databases.add(row[BibAttrs.DBID])
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
            to_lower_if_not_none(row[BibAttrs.IN_OR_BY]),
            to_lower_if_not_none(row[BibAttrs.SUBTITLE]),
            to_lower_if_not_none(row[BibAttrs.COMMENT]),
            to_lower_if_not_none(row[BibAttrs.ABSTRACT]),
            to_lower_if_not_none(row[BibAttrs.KEYWORDS]),
        ]

        for word in full_text:
            if word not in ' '.join(model_full_text_data):
                return False

        matched_databases.add(row[BibAttrs.DBID])
        return True

    # ———————————————————————————————————————————————————————————— do “actions”

    def do_startup(self):
        Gtk.Application.do_startup(self)

        # Comes from GtkCssAwareMixin.
        self.setup_resources_and_css()

        self.setup_actions()
        self.setup_app_menu()

    def do_notification(self, message):

        notification = Notify.Notification.new('Bibed', message)
        # notification.set_timeout(Notify.EXPIRES_NEVER)
        # notification.add_action('quit', 'Quit', notification_callback)
        notification.show()

    def do_activate(self):

        # assert lprint_function_name()

        LOGGER.debug('Startup time (GTK setup): {}'.format(
            seconds_to_string(time.time() - self.time_start)))

        # We only allow a single window and raise any existing ones
        if self.window:
            LOGGER.info('Window already loaded somewhere, focusing it.')

        else:
            from bibed.gui.window import BibedWindow

            Notify.init(APP_NAME)

            self.session_prepare()

            # HEADS UP: passing application argument is MANDATORY for the
            #           whole Gtk application & main loop to work correctly.
            self.window = BibedWindow(title='Main Window', application=self)

            # As soon as the main window is here, keep the splash above it.
            self.splash.set_transient_for(self.window)

            if preferences.remember_open_files and memories.open_files:
                run_and_wait_on(self.session_restore)

            self.session_finish()

        self.close_splash()

        LOGGER.debug('Startup time (including session restore): {}'.format(
            seconds_to_string(time.time() - self.time_start)))

        self.window.present()

    def do_command_line(self, command_line):

        # assert lprint_function_name()

        options = command_line.get_options_dict()

        # convert GVariantDict -> GVariant -> dict
        options = options.end().unpack()

        if 'test' in options:
            LOGGER.info("Test argument received: %s" % options['test'])

        self.activate()

        return 0

    def run(self, *args, **kwargs):

        # assert lprint_function_name()

        try:
            super().run(*args, **kwargs)

        except KeyboardInterrupt:
            LOGGER.warning('Interrupted, terminating properly…')
            self.on_quit(None, None)

    # ———————————————————————————————————————————————————————— Session & splash

    def close_splash(self):

        self.splash.destroy()
        self.splash = None

    def session_prepare(self):

        # assert lprint_function_name()

        # Needed for the thread to prepare things for the main loop.
        self.session = Anything()
        self.session.search_grab_focus = False
        self.session.databases_to_select = []
        self.session.filenames_to_select = []

    def session_restore(self):

        # assert lprint_function_name()

        self.splash.set_status(
            _('Loading {} file(s) and restoring previous session…').format(
                len(memories.open_files)))

        # 1: search_text needs to be loaded first, else it gets
        # wiped when file_combo is updated with re-loaded files.
        # 2: don't load it if there are no open_files.
        # 3: dont call do_filter_data_store(), it will be called
        # by on_files_combo_changed() when files are added.
        if memories.search_text is not None:
            self.window.search.set_text(memories.search_text)
            self.session.search_grab_focus = True

        # Idem, same problem.
        if memories.selected_filenames is not None:
            self.session.filenames_to_select = memories.selected_filenames

        else:
            self.session.filenames_to_select = memories.open_files.copy()

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
                    if filename in self.session.filenames_to_select:
                        # we have to convert filenames to databases
                        # because all of this seems to happen too
                        # fast for store to be ready to return
                        # .get_database() results before the end
                        # of the current method.
                        self.session.databases_to_select.append(database)

    def session_finish(self):

        # assert lprint_function_name()

        if sorted(self.session.filenames_to_select) != sorted(
                [x.filename for x in self.session.databases_to_select]):
            # Most probably a system file was selected before closing.
            # Try to get it again.

            for filename in self.session.filenames_to_select:
                for system_database in controllers.files.system_databases:
                    if filename == system_database.filename:
                        self.session.databases_to_select.append(system_database)

        self.window.show_all()

        if self.session.databases_to_select:
            self.window.set_selected_databases(self.session.databases_to_select)

            # Selecting a system database is the only case that doesn't
            # trigger a full window / treeview update. Fake it.
            if len(tuple(controllers.files.selected_system_databases)):
                self.window.on_selected_files_changed()
        else:
            if not controllers.files.num_user:
                # No database. Trigger a treeview filter
                # anyway to hide the system entries if any.
                self.window.on_selected_files_changed()
                self.window.do_activate()

            else:
                self.window.files_popover.listbox.select_all()

        if self.session.search_grab_focus:
            self.window.searchbar.set_search_mode(True)
            self.window.search.grab_focus()

        # not necessary anymore.
        del self.session

    # ———————————————————————————————————————————— higher level file operations

    def create_file(self, filename):
        ''' Create a new BIB file, then open it in the application. '''

        # assert lprint_function_name()

        touch_file(filename)

        self.open_file(filename)

    def open_file(self, filename, select=True):
        ''' Add a file to the application. '''

        # assert lprint_function_name()
        # assert lprint(filename)

        # Be sure we keep a consistent path across all application.
        filename = os.path.realpath(os.path.abspath(filename))

        try:
            # Note: via events, this will update the window title.
            database = controllers.files.load(filename)

        except AlreadyLoadedException:
            self.do_notification(
                _('“{}” already loaded.').format(filename))
            # TODO: Select / Focus the file.
            return

        except Exception as e:
            message = NO_('Cannot load file “{file}”: {error}')
            LOGGER.exception(message.format(file=filename, error=e))

            self.window.do_status_change(_(message).format(
                file=filename, error=e))
            return

        if select:
            self.window.set_selected_databases([database])

        # Needed for correct session reload.
        return database

    def reload_databases(self, message=None):

        # assert lprint_function_name()
        # assert lprint(message)

        for database in controllers.files.user_databases:
            self.reload_database(database)

        if message:
            self.window.do_status_change(message)

    def reload_database(self, database, message=None):

        # assert lprint_function_name()
        # assert lprint(filename, message)

        if controllers.files.reload(database):
            if message:
                self.window.do_status_change(message)

    def close_database(self, database, save_before=False, remember_close=True):
        ''' Close a file and impact changes. '''

        # assert lprint_function_name()

        controllers.files.close(
            database,
            save_before=save_before,
            remember_close=remember_close
        )

    # ———————————————————————————————————————————————————————————— on “actions”

    def on_about(self, action, param):

        # assert lprint_function_name()

        about_dialog = Gtk.AboutDialog(
            transient_for=self.window, modal=True)

        about_dialog.set_program_name(APP_NAME)
        about_dialog.set_version(APP_VERSION)

        # logo = self.icon_theme.load_icon('logo', 128, 0)
        # about_dialog.set_logo(logo)
        about_dialog.set_logo_icon_name('bibed-logo')

        about_dialog.set_copyright(_('© Cocoliv.es Collective'))

        comments = (
            _('Bibliographic assistance libre software')
            + '\n\nGTK v{}.{}.{}\n'
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
                    '\n'
                    + _('Sentry SDK v{sdk_vers}, reporting to\n{dsn}\n'
                        '(see {website} for details)'
                        '{last}').format(
                        sdk_vers=sentry_sdk.VERSION,
                        dsn=gpod('sentry_dsn'),
                        website=gpod('sentry_url'),
                        last=_('<big>Last event ID: {}</big>').format(last_event)
                        if last_event else ''
                    )
                )

        about_dialog.set_comments(comments)

        about_dialog.set_website('https://bibed.cocoliv.es/')
        about_dialog.set_website_label(_('{app} website').format(app=APP_NAME))
        about_dialog.set_license_type(Gtk.License.GPL_3_0_ONLY)

        about_dialog.set_authors([
            'Olivier Cortès <olive@cocoliv.es>',
            'Collectif Cocoliv.es <contact@cocoliv.es>',
        ])
        about_dialog.set_documenters([
            'Olivier Cortès <olive@cocoliv.es>',
        ])
        about_dialog.set_artists([
            'Corinne Carnevali <coco@cocoliv.es>',
            'Timothée Cortès <tim@cocoliv.es>',
        ])
        about_dialog.set_translator_credits(
            'Olivier Cortès <olive@cocoliv.es>'
        )

        about_dialog.add_credit_section('Supporters', [
            'Timothée Cortès <tim@cocoliv.es>',
            'Anaïs Cortès <ana@cocoliv.es>',
            'Louise Cortès Carnevali <lou@cocoliv.es>',
        ])
        # https://lazka.github.io/pgi-docs/Gtk-3.0/classes/AboutDialog.html#Gtk.AboutDialog.add_credit_section

        about_dialog.present()

    def on_quit(self, action, param):

        if self.is_quitting:
            return

        self.is_quitting = True

        # Hide the window immediately to fake reactivity
        # in case there are still pending events.
        self.window.hide()

        # Block signals, else memories.combo_filename will
        # finish empty When last file has been closed.
        self.window.block_signals()

        # This will close system files too.
        controllers.files.close_all(

            # Save is done along-the-way at each user action that needs it.
            save_before=False,

            # This will allow automatic reopen on next launch.
            remember_close=False,
        )

        wait_for_queued_events()

        self.quit()

        LOGGER.info(
            'Terminating application; ran {}.'.format(
                seconds_to_string(time.time() - self.time_start)))

        for handler in self.logging_handlers:
            handler.close()

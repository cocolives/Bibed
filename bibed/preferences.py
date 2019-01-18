
import logging

from bibed.constants import (
    APP_NAME,
    BOXES_BORDER_WIDTH,
)

from bibed.utils import (
    get_user_home_directory,
    make_bibed_user_dir,
    ApplicationDefaults,
    UserPreferences,
    UserMemories,
)

from bibed.uihelpers import (
    label_with_markup,
    grid_with_common_params,
    vbox_with_icon_and_label,
)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk, Gdk, Pango  # NOQA

LOGGER = logging.getLogger(__name__)


# —————————————————————————————————————————————————————————————— Classes


class BibedPreferencesDialog(Gtk.Dialog):

    def __init__(self, parent):
        Gtk.Dialog.__init__(
            self, "{0} Preferences".format(APP_NAME), parent, 0)

        self.set_modal(True)
        self.set_default_size(800, 500)
        self.set_border_width(BOXES_BORDER_WIDTH)

        box = self.get_content_area()

        # label = Gtk.Label("Preferences")
        # box.add(label)

        self.notebook = Gtk.Notebook()
        self.notebook.set_tab_pos(Gtk.PositionType.LEFT)

        box.add(self.notebook)

        self.setup_page_general()
        self.setup_page_accels()
        self.setup_page_formats()

        self.show_all()

    def setup_page_general(self):

        def build_fcbwf():
            # HEADS UP: don't useGtk.FileChooserButton(…),
            # it doesn't honor parameters.
            fcbwf = Gtk.FileChooserButton.new(
                'Select working folder',
                Gtk.FileChooserAction.SELECT_FOLDER
            )
            fcbwf.set_current_folder(
                preferences.working_folder or get_user_home_directory())
            fcbwf.connect('file-set', self.on_working_folder_set)

            return fcbwf

        def build_swbas():

            switch = Gtk.Switch()
            switch.connect(
                'notify::active',
                self.on_switch_bib_auto_save_activated)

            switch.set_active(
                defaults.bib_auto_save
                if preferences.bib_auto_save is None
                else preferences.bib_auto_save)

            return switch

        def build_spkrf():

            adjustment = Gtk.Adjustment(
                defaults.keep_recent_files
                if preferences.keep_recent_files is None
                else preferences.keep_recent_files,
                -1, 20, 1, 10, 0)

            spin = Gtk.SpinButton()
            spin.set_adjustment(adjustment)
            spin.connect('value-changed',
                         self.on_spin_keep_recent_files_changed)
            spin.connect('change-value',
                         self.on_spin_keep_recent_files_changed)
            spin.set_numeric(True)
            spin.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)

            return spin

        def build_swrof():

            switch = Gtk.Switch()
            switch.connect(
                'notify::active',
                self.on_switch_remember_open_files_activated)

            switch.set_active(
                defaults.remember_open_files
                if preferences.remember_open_files is None
                else preferences.remember_open_files)

            return switch

        pg = grid_with_common_params()

        # ————————————————————————————————————————————————— Working folder

        self.fcb_working_folder = build_fcbwf()
        self.lbl_working_folder = label_with_markup(
            '<b>Working folder</b>\n'
            '<span foreground="grey" size="small">'
            'Where your BIB files are stored.</span>')

        pg.attach(
            self.lbl_working_folder,
            # left, top, width, height
            0, 0, 1, 1)

        pg.attach_next_to(
            self.fcb_working_folder,
            self.lbl_working_folder,
            Gtk.PositionType.RIGHT,
            3, 1)

        # —————————————————————————————————————————————————— BIB auto save

        self.swi_bib_auto_save = build_swbas()
        self.lbl_bib_auto_save = label_with_markup(
            '<b>Automatic save</b>\n'
            '<span foreground="grey" size="small">'
            'Save BIB changes automatically while editing.</span>')

        pg.attach_next_to(
            self.lbl_bib_auto_save,
            self.lbl_working_folder,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pg.attach_next_to(
            self.swi_bib_auto_save,
            self.lbl_bib_auto_save,
            Gtk.PositionType.RIGHT,
            1, 1)

        # —————————————————————————————————————————————— Keep recent files

        self.spi_keep_recent_files = build_spkrf()
        self.lbl_keep_recent_files = label_with_markup(
            '<b>Remember recent files</b>\n'
            '<span foreground="grey" size="small">'
            'Remember this much BIB files recently opened.\n'
            'Set to 0 to disable remembering, or -1 for infinite.</span>')

        pg.attach_next_to(
            self.lbl_keep_recent_files,
            self.lbl_bib_auto_save,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pg.attach_next_to(
            self.spi_keep_recent_files,
            self.lbl_keep_recent_files,
            Gtk.PositionType.RIGHT,
            1, 1)

        # ———————————————————————————————————————————— Remember open files

        self.swi_remember_open_files = build_swrof()
        self.lbl_remember_open_files = label_with_markup(
            '<b>Remember open files</b>\n'
            '<span foreground="grey" size="small">'
            'When launching application, re-open automatically files\n'
            'which were previously opened before quitting last session.'
            '</span>')

        pg.attach_next_to(
            self.lbl_remember_open_files,
            self.lbl_keep_recent_files,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pg.attach_next_to(
            self.swi_remember_open_files,
            self.lbl_remember_open_files,
            Gtk.PositionType.RIGHT,
            1, 1)

        # ———————————————————————————————————————————————————— End widgets

        self.page_general = pg

        self.notebook.append_page(
            self.page_general,
            vbox_with_icon_and_label(
                'preferences-system-symbolic',
                'General'
            )
        )

    def setup_page_accels(self):

        pa = grid_with_common_params()

        pa.add(Gtk.Label('Accelerators preferences'))

        self.page_accels = pa

        self.notebook.append_page(
            self.page_accels,
            vbox_with_icon_and_label(
                'preferences-desktop-keyboard-shortcuts-symbolic',
                'Accelerators'
            )
        )

    def setup_page_formats(self):

        pf = grid_with_common_params()

        pf.add(Gtk.Label('Formats preferences'))

        self.page_formats = pf

        self.notebook.append_page(
            self.page_formats,
            vbox_with_icon_and_label(
                'preferences-desktop-locale-symbolic',
                'Formats'
            )
        )

    def on_working_folder_set(self, widget):

        new_folder = self.fcb_working_folder.get_filename()

        if new_folder != preferences.working_folder:

            LOGGER.info(
                'on_working_folder_changed(): set to {}'.format(new_folder))

            preferences.working_folder = new_folder

    def on_switch_bib_auto_save_activated(self, switch, gparam):

        is_active = switch.get_active()

        # We need to test, else the set_active() call in dialog
        # constructor triggers a superflous preferences save().
        if preferences.bib_auto_save != is_active:
            preferences.bib_auto_save = is_active

    def on_switch_remember_open_files_activated(self, switch, gparam):

        is_active = switch.get_active()

        # We need to test, else the set_active() call in dialog
        # constructor triggers a superflous preferences save().
        if preferences.remember_open_files != is_active:
            preferences.remember_open_files = is_active

    def on_spin_keep_recent_files_changed(self, adj):

        value = int(adj.get_value())

        if preferences.keep_recent_files is None:
            preferences.keep_recent_files = value

        else:
            # Need to test to avoid double (and useless) save().
            if preferences.keep_recent_files != value:
                preferences.keep_recent_files = value

# ————————————————————————————————————————————————— preferences singletons


make_bibed_user_dir()


defaults    = ApplicationDefaults()
preferences = UserPreferences(defaults=defaults)
memories    = UserMemories(defaults=defaults, preferences=preferences)

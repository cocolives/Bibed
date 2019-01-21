
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
    widget_expand_align,
    grid_with_common_params,
    vbox_with_icon_and_label,
)

from bibed.gtk import Gtk

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

        self.notebook = Gtk.Notebook()
        self.notebook.set_tab_pos(Gtk.PositionType.LEFT)

        box.add(self.notebook)

        box.add(widget_expand_align(label_with_markup(
            '<span foreground="grey">Preferences are automatically saved; '
            'just hit <span face="monospace">ESC</span> when you are done.'
            '</span>',
            xalign=0.5
        ), expand=True, halign=Gtk.Align.CENTER))

        self.setup_page_general()
        self.setup_page_accels()
        self.setup_page_formats()

        self.connect('hide', self.on_preferences_hide)

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

            switch = widget_expand_align(Gtk.Switch())

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

            spin = widget_expand_align(Gtk.SpinButton())
            spin.set_adjustment(adjustment)
            spin.connect('value-changed',
                         self.on_spin_keep_recent_files_changed)
            spin.connect('change-value',
                         self.on_spin_keep_recent_files_changed)
            spin.set_numeric(True)
            spin.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)

            return spin

        def build_swrof():

            switch = widget_expand_align(Gtk.Switch())

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
            1, 1)

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
            '<b>Remember session</b>\n'
            '<span foreground="grey" size="small">'
            'When launching application, automatically re-open files\n'
            'which were previously opened before quitting last session,\n'
            'restore search query, filters and sorting.</span>')

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

        def build_cbtcs():

            prefs = preferences.accelerators.copy_to_clipboard_single
            defls = defaults.accelerators.copy_to_clipboard_single
            prefsv = preferences.accelerators.copy_to_clipboard_single_value
            deflsv = defaults.accelerators.copy_to_clipboard_single_value

            if prefs is not None:
                options = prefs.copy() + defls.copy()

            else:
                options = defls.copy()

            combo = Gtk.ComboBoxText.new_with_entry()
            combo.set_entry_text_column(0)
            combo.set_size_request(300, 10)

            combo.connect('changed', self.on_combo_single_copy_changed)

            for option in options:
                combo.append_text(option)

            if prefsv is None:
                combo.set_active(options.index(deflsv))

            else:
                combo.set_active(options.index(prefsv))

            return combo

        pa = grid_with_common_params()

        # —————————————————————————————————————————————— Single Clipboard

        defsigval = defaults.accelerators.copy_to_clipboard_single_value

        self.cbt_copy_single = build_cbtcs()
        self.lbl_copy_single = label_with_markup(
            '<b>Single selection copy to clipboard</b>\n'
            '<span size="small" color="grey">'
            'When you select only one entry in the list.</span>')

        self.lbl_copy_single_help = label_with_markup(
            '<span size="small"><span color="grey">'
            'Type any other pattern to create your own, using '
            '<span color="lightgrey"><tt>@@key@@</tt></span> '
            'anywhere inside.</span>\n'
            '<span color="red">WARNING: </span>'
            '<span color="grey">any error in your pattern will '
            'make it replaced with application default, '
            'aka <span color="lightgrey"><tt>{0}</tt></span>.'
            '</span></span>'.format(defsigval))

        pa.attach(
            self.lbl_copy_single,
            # left, top, width, height
            0, 0, 1, 1)

        pa.attach_next_to(
            self.cbt_copy_single,
            self.lbl_copy_single,
            Gtk.PositionType.RIGHT,
            1, 1)
        pa.attach_next_to(
            self.lbl_copy_single_help,
            self.lbl_copy_single,
            Gtk.PositionType.BOTTOM,
            2, 1)

        # ———————————————————————————————————————————————————— End widgets

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

    def on_combo_single_copy_changed(self, combo):

        # Note: see self.on_preferences_hide()

        option = combo.get_active_text()

        preferences.accelerators.copy_to_clipboard_single_value = option
        preferences.save()

    def on_preferences_hide(self, window):

        # This operation cannot be done while user is typing new accels,
        # else every char-typing is saved as a new entry, which makes a
        # lot of false positives.
        self.save_accelerators()

    def save_accelerators(self):

        option = preferences.accelerators.copy_to_clipboard_single_value

        defls = defaults.accelerators.copy_to_clipboard_single
        prefs = preferences.accelerators.copy_to_clipboard_single

        if option not in defls:
            if prefs is None:
                preferences.accelerators.copy_to_clipboard_single = [option]
                preferences.save()
            else:
                if option not in prefs:
                    prefs += [option]
                    preferences.save()


# ————————————————————————————————————————————————— preferences singletons


make_bibed_user_dir()


defaults    = ApplicationDefaults()
preferences = UserPreferences(defaults=defaults)
memories    = UserMemories(defaults=defaults,
                           preferences=preferences)

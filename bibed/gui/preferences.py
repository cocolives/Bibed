
import logging

from bibed.constants import (
    APP_NAME,
    BOXES_BORDER_WIDTH,
    GRID_ROWS_SPACING,
)

from bibed.utils import get_user_home_directory
from bibed.preferences import defaults, preferences

from bibed.gui.helpers import (
    label_with_markup,
    widget_properties,
    frame_defaults,
    grid_with_common_params,
    vbox_with_icon_and_label,
    # debug_widget,
)
from bibed.gui.dndflowbox import DnDFlowBox
from bibed.gui.gtk import Gtk

LOGGER = logging.getLogger(__name__)


def dnd_scrolled_flowbox(name=None, title=None, dialog=None):

    if title is None:
        title = name.title()

    frame = frame_defaults(title)

    scrolled = Gtk.ScrolledWindow()

    scrolled.set_policy(Gtk.PolicyType.NEVER,
                        Gtk.PolicyType.AUTOMATIC)

    # debug_widget(scrolled)

    flowbox = widget_properties(
        DnDFlowBox(name=name, dialog=dialog),
        expand=True,
    )

    # flowbox.set_valign(Gtk.Align.START)
    flowbox.set_max_children_per_line(3)
    flowbox.set_min_children_per_line(2)

    flowbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
    # flowbox.set_activate_on_single_click(False)

    scrolled.add(flowbox)
    frame.add(scrolled)

    # scrolled.set_size_request(100, 100)
    flowbox.set_size_request(100, 100)

    return frame, scrolled, flowbox


# —————————————————————————————————————————————————————————————————— Classes


class BibedPreferencesDialog(Gtk.Dialog):

    def __init__(self, parent):
        Gtk.Dialog.__init__(
            self, "{0} Preferences".format(APP_NAME), parent, 0)

        self.set_modal(True)

        # TODO: get screen resolution to make HiDPI aware.
        self.set_default_size(500, 300)

        self.set_border_width(BOXES_BORDER_WIDTH)
        self.connect('hide', self.on_preferences_hide)

        box = self.get_content_area()

        self.notebook = Gtk.Notebook()
        self.notebook.set_tab_pos(Gtk.PositionType.LEFT)

        box.add(self.notebook)

        box.add(widget_properties(label_with_markup(
            '<span foreground="grey">Preferences are automatically saved; '
            'just hit <span face="monospace">ESC</span> when you are done.'
            '</span>',
            xalign=0.5),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.CENTER,
            margin_top=5))

        self.setup_page_general()
        self.setup_page_accels()
        self.setup_page_creator()
        # self.setup_page_editor()

        self.show_all()

    def setup_page_general(self):

        def build_fcbwf():
            # HEADS UP: don't useGtk.FileChooserButton(…),
            # it doesn't honor parameters.
            fcbwf = widget_properties(
                Gtk.FileChooserButton.new(
                    'Select working folder',
                    Gtk.FileChooserAction.SELECT_FOLDER
                ),
                halign=Gtk.Align.START,
                valign=Gtk.Align.CENTER
            )
            fcbwf.set_current_folder(
                preferences.working_folder or get_user_home_directory())
            fcbwf.connect('file-set', self.on_working_folder_set)

            return fcbwf

        def build_swbas():

            switch = widget_properties(
                Gtk.Switch(),
                halign=Gtk.Align.START,
                valign=Gtk.Align.CENTER
            )

            switch.connect(
                'notify::active',
                self.on_switch_bib_auto_save_activated)

            switch.set_active(
                defaults.bib_auto_save
                if preferences.bib_auto_save is None
                else preferences.bib_auto_save)

            return switch

        def build_spkrf():

            spin = widget_properties(
                Gtk.SpinButton(),
                halign=Gtk.Align.START,
                valign=Gtk.Align.CENTER
            )

            adjustment = Gtk.Adjustment(
                defaults.keep_recent_files
                if preferences.keep_recent_files is None
                else preferences.keep_recent_files,
                -1, 20, 1, 10, 0
            )

            spin.set_adjustment(adjustment)
            spin.connect('value-changed',
                         self.on_spin_keep_recent_files_changed)
            spin.connect('change-value',
                         self.on_spin_keep_recent_files_changed)
            spin.set_numeric(True)
            spin.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)

            return spin

        def build_swrof():

            switch = widget_properties(
                Gtk.Switch(),
                halign=Gtk.Align.START,
                valign=Gtk.Align.CENTER
            )

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
        self.lbl_working_folder = widget_properties(label_with_markup(
            '<b>Working folder</b>\n'
            '<span foreground="grey" size="small">'
            'Where your BIB files are stored.</span>'),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER,
        )

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
        self.lbl_bib_auto_save = widget_properties(label_with_markup(
            '<b>Automatic save</b>\n'
            '<span foreground="grey" size="small">'
            'Save BIB changes automatically while editing.</span>'),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER,
        )

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
        self.lbl_keep_recent_files = widget_properties(label_with_markup(
            '<b>Remember recent files</b>\n'
            '<span foreground="grey" size="small">'
            'Remember this much BIB files recently opened.\n'
            'Set to 0 to disable remembering, or -1 for infinite.</span>'),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER,
        )

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
        self.lbl_remember_open_files = widget_properties(label_with_markup(
            '<b>Remember session</b>\n'
            '<span foreground="grey" size="small">'
            'When launching application, automatically re-open files\n'
            'which were previously opened before quitting last session,\n'
            'restore search query, filters and sorting.</span>'),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER,
        )

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
        self.lbl_copy_single = widget_properties(label_with_markup(
            '<b>Single selection copy to clipboard</b>\n'
            '<span size="small" color="grey">'
            'When you select only one entry in the list.</span>'),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER,
        )

        self.lbl_copy_single_help = widget_properties(label_with_markup(
            '<span size="small"><span color="grey">'
            'Type any other pattern to create your own, using '
            '<span color="lightgrey"><tt>@@key@@</tt></span> '
            'anywhere inside.</span>\n'
            '<span color="red">WARNING: </span>'
            '<span color="grey">any error in your pattern will '
            'make it replaced with application default, '
            'aka <span color="lightgrey"><tt>{0}</tt></span>.'
            '</span></span>'.format(defsigval)),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER,  # TODO: not START ?
        )

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

    def setup_page_creator(self):

        def build_dnd(qualify, title):

            defl_main  = defaults.types.main
            defl_other = defaults.types.other
            pref_main  = preferences.types.main
            pref_other = preferences.types.other

            (frame, scrolled, dnd_area) = dnd_scrolled_flowbox(
                name=qualify, title=title, dialog=self)

            if qualify == 'main':
                children = defl_main if pref_main is None else pref_main

            else:
                children = defl_other if pref_other is None else pref_other
                # dnd_area.drag_source_set_icon_name(Gtk.STOCK_GO_BACK)

            dnd_area.add_items(children)

            return (frame, scrolled, dnd_area)

        pc = grid_with_common_params()

        (self.fr_creator_dnd_main,
         self.sw_creator_dnd_main,
         self.fb_creator_dnd_main) = build_dnd('main', '   Main types   ')
        (self.fr_creator_dnd_other,
         self.sw_creator_dnd_other,
         self.fb_creator_dnd_other) = build_dnd('other', '   Other types   ')

        self.lbl_creator = widget_properties(label_with_markup(
            '<big>Main and other entry types</big>\n'
            '<span foreground="grey">'
            'Drag and drop items from one side to another\n'
            'to have</span> main <span foreground="grey">'
            'items displayed first in entry\n'
            'creator assistant, and</span> other '
            '<span foreground="grey">accessible\n'
            'in a folded area of the assistant.\n\n'
            'Note: they will appear in the exact order\n'
            'you organize them into.'
            '</span>'),
            expand=False,
            halign=Gtk.Align.START,
            valign=Gtk.Align.START)

        self.btn_creator_reset = widget_properties(
            Gtk.Button('Reset to defaults'),
            expand=False,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.END,
            margin_top=GRID_ROWS_SPACING,
            margin_bottom=GRID_ROWS_SPACING)

        self.btn_creator_reset.connect('clicked', self.on_creator_reset)

        if preferences.types.main or preferences.types.other:
            self.btn_creator_reset.set_sensitive(True)

        # debug_widget(self.lbl_creator)
        pc.attach(
            self.lbl_creator,
            0, 0, 1, 1
        )

        pc.attach_next_to(
            self.btn_creator_reset,
            self.lbl_creator,
            Gtk.PositionType.BOTTOM,
            1, 1
        )

        pc.attach_next_to(
            self.fr_creator_dnd_main,
            self.lbl_creator,
            Gtk.PositionType.RIGHT,
            1, 2
        )

        pc.attach_next_to(
            self.fr_creator_dnd_other,
            self.fr_creator_dnd_main,
            Gtk.PositionType.RIGHT,
            1, 2
        )

        self.page_creator = pc

        self.notebook.append_page(
            self.page_creator,
            vbox_with_icon_and_label(
                'document-new-symbolic',
                'Creator'
            )
        )

    def setup_page_editor(self):

        def build_cbtet():

            prefs = defaults.fields
            defls = defaults.fields
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

        pf = grid_with_common_params()

        self.cbt_entry_type = build_cbtet()

        pf.attach(self.cbt_entry_type)

        pf.attach_next_to(widget_properties(label_with_markup(
            '<span foreground="grey">Preferences are automatically saved; '
            'just hit <span face="monospace">ESC</span> when you are done.'
            '</span>',
            xalign=0.5),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.CENTER)
        )

        self.page_formats = pf

        self.notebook.append_page(
            self.page_formats,
            vbox_with_icon_and_label(
                'document-edit-symbolic',
                'Editor'
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

    def on_creator_reset(self, button):

        del preferences.types.main
        del preferences.types.other

        preferences.save()

        self.fb_creator_dnd_main.remove_items()
        self.fb_creator_dnd_main.add_items(defaults.types.main)

        self.fb_creator_dnd_other.remove_items()
        self.fb_creator_dnd_other.add_items(defaults.types.other)

        self.btn_creator_reset.set_sensitive(False)

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

    def update_dnd_preferences(self):

        save = False

        creator_main = self.fb_creator_dnd_main.get_children_names()
        creator_other = self.fb_creator_dnd_other.get_children_names()

        if preferences.types.main != creator_main:
            preferences.types.main = creator_main
            save = True

        if preferences.types.other != creator_other:
            preferences.types.other = creator_other
            save = True

        # TODO: add other DND preferences

        if save:
            preferences.save()
            self.btn_creator_reset.set_sensitive(True)

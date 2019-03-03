
import logging

from bibed.constants import (
    APP_NAME,
    BOXES_BORDER_WIDTH,
    GRID_ROWS_SPACING,
)

from bibed.locale import _
from bibed.user import get_user_home_directory
from bibed.sentry import sentry
from bibed.preferences import defaults, preferences, gpod
from bibed.regex import OWNER_NAME_RE
from bibed.controllers import controllers
from bibed.gtk import Gtk

from bibed.gui.helpers import (
    in_scrolled,
    label_with_markup,
    widget_properties,
    add_classes, remove_classes,
    grid_with_common_params,
    vbox_with_icon_and_label,
    build_label_and_switch,
    build_entry_field_labelled_entry,
)
from bibed.gui.dndflowbox import dnd_scrolled_flowbox


LOGGER = logging.getLogger(__name__)


# —————————————————————————————————————————————————————————————————— Classes


class BibedPreferencesDialog(Gtk.Dialog):

    def __init__(self, parent):
        Gtk.Dialog.__init__(
            self, _('{app} Preferences').format(app=APP_NAME), parent, 0)

        self.set_modal(True)

        # TODO: get screen resolution to make HiDPI aware.
        self.set_default_size(450, 350)

        self.set_border_width(BOXES_BORDER_WIDTH)

        # self.connect('hide', self.on_preferences_hide)

        box = self.get_content_area()

        self.notebook = Gtk.Notebook()
        self.notebook.set_tab_pos(Gtk.PositionType.LEFT)

        box.add(self.notebook)

        box.add(widget_properties(label_with_markup(
            _('<span foreground="grey">Preferences are automatically saved. '
              'Hit <span face="monospace">Esc</span> when you are done.'
              '</span>'),
            xalign=0.5),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.CENTER,
            margin_top=5))

        self.setup_page_general()
        self.setup_page_accels()
        self.setup_page_creator_editor()
        self.setup_page_interface_customization()
        self.setup_finish()

        self.show_all()

    def setup_page_general(self):

        def build_folder_combobox(chooser_title, chooser_current_folder, chooser_set_callback):
            # HEADS UP: don't useGtk.FileChooserButton(…),
            # it doesn't honor parameters.
            fcbwf = widget_properties(
                Gtk.FileChooserButton.new(
                    chooser_title,
                    Gtk.FileChooserAction.SELECT_FOLDER
                ),
                halign=Gtk.Align.START,
                valign=Gtk.Align.CENTER
            )
            fcbwf.set_current_folder(chooser_current_folder)
            fcbwf.connect('file-set', chooser_set_callback)

            return fcbwf

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

        pg = grid_with_common_params()

        # ——————————————————————————————————————————————— Bibliographies folder

        self.fcb_working_folder = build_folder_combobox(
            _('Select bibliographies folder'),
            preferences.working_folder or get_user_home_directory(),
            self.on_working_folder_set,
        )
        self.lbl_working_folder = widget_properties(label_with_markup(
            _('<b>Bibliographies folder</b>\n'
              '<span foreground="grey" size="small">'
              'Where your BIB files are stored / created.</span>'),
            line_wrap=True),
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

        # ————————————————————————————————————————————————————————— PDFs folder

        self.fcb_books_folder = build_folder_combobox(
            _('Select Books folder'),
            preferences.books_folder or get_user_home_directory(),
            self.on_books_folder_set,

        )
        self.lbl_books_folder = widget_properties(label_with_markup(
            _('<b>Books folder</b>\n'
              '<span foreground="grey" size="small">'
              'Where your PDF files (books, booklets, prints, articles…) '
              'are stored.</span>'),
            line_wrap=True),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER,
        )

        pg.attach_next_to(
            self.lbl_books_folder,
            self.lbl_working_folder,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pg.attach_next_to(
            self.fcb_books_folder,
            self.lbl_books_folder,
            Gtk.PositionType.RIGHT,
            1, 1)

        # —————————————————————————————————————————————————— BIB auto save

        (self.lbl_bib_auto_save,
         self.swi_bib_auto_save) = build_label_and_switch(
            _('<b>Automatic save</b>\n'
              '<span foreground="grey" size="small">'
              'Save BIB changes automatically while editing.</span>'),
            self.on_switch_activated,
            gpod('bib_auto_save'),
            func_args=('bib_auto_save', ),
            label_options={'line_wrap': True},
        )

        pg.attach_next_to(
            self.lbl_bib_auto_save,
            self.lbl_books_folder,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pg.attach_next_to(
            self.swi_bib_auto_save,
            self.lbl_bib_auto_save,
            Gtk.PositionType.RIGHT,
            1, 1)

        # TODO: add a switch for 'backup_before_save'

        (self.lbl_ensure_biblatex_checks,
         self.swi_ensure_biblatex_checks) = build_label_and_switch(
            _('<b>Ensure BibLaTeX requirements</b>\n'
              '<span foreground="grey" size="small">'
              'Before saving new entries, ensure that BibLaTeX conditions '
              'and requirements are met (for example one of <span '
              'face="monospace">date</span> or <span face="monospace">'
              'year</span> fields are filled on articles).</span>'),
            self.on_switch_activated,
            gpod('ensure_biblatex_checks'),
            func_args=('ensure_biblatex_checks', ),
            label_options={'line_wrap': True},
        )

        # TODO: implement the feature and enable the switch.
        self.swi_ensure_biblatex_checks.set_sensitive(False)

        pg.attach_next_to(
            self.lbl_ensure_biblatex_checks,
            self.lbl_bib_auto_save,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pg.attach_next_to(
            self.swi_ensure_biblatex_checks,
            self.lbl_ensure_biblatex_checks,
            Gtk.PositionType.RIGHT,
            1, 1)

        # —————————————————————————————————————————————— Keep recent files

        self.spi_keep_recent_files = build_spkrf()
        self.lbl_keep_recent_files = widget_properties(label_with_markup(
            _('<b>Remember recent files</b>\n'
              '<span foreground="grey" size="small">'
              'Remember this much BIB files recently opened.\n'
              'Set to 0 to disable remembering, or -1 for infinite.</span>'),
            line_wrap=True),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER,
        )

        pg.attach_next_to(
            self.lbl_keep_recent_files,
            self.lbl_ensure_biblatex_checks,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pg.attach_next_to(
            self.spi_keep_recent_files,
            self.lbl_keep_recent_files,
            Gtk.PositionType.RIGHT,
            1, 1)

        # ———————————————————————————————————————————— Remember open files

        (self.lbl_remember_open_files,
         self.swi_remember_open_files) = build_label_and_switch(
            _('<b>Remember session</b>\n'
              '<span foreground="grey" size="small">'
              'When launching application, automatically re-open files '
              'which were previously opened before quitting last session, '
              'restore search query, filters and sorting.</span>'),
            self.on_switch_activated,
            gpod('remember_open_files'),
            func_args=('remember_open_files', ),
            label_options={'line_wrap': True},
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

        # ——————————————————————————————————————————Remember windows states

        (self.lbl_remember_windows_states,
         self.swi_remember_windows_states) = build_label_and_switch(
            _('<b>Remember windows states</b>\n'
              '<span foreground="grey" size="small">'
              'Restore main window and dialogs sizes and positions '
              'across sessions.</span>'),
            self.on_switch_activated,
            gpod('remember_windows_states'),
            func_args=('remember_windows_states', ),
            label_options={'line_wrap': True},
        )

        pg.attach_next_to(
            self.lbl_remember_windows_states,
            self.lbl_remember_open_files,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pg.attach_next_to(
            self.swi_remember_windows_states,
            self.lbl_remember_windows_states,
            Gtk.PositionType.RIGHT,
            1, 1)

        # —————————————————————————————————————————————————————————————— Sentry

        (self.lbl_use_sentry,
         self.swi_use_sentry) = build_label_and_switch(
            _('<b>Report issues to developers</b>\n'
              '<span foreground="grey" size="small">'
              'Enabling this will automatically send errors, crashes and '
              'debugging data to developpers, anonymously. '
              'We use <span face="monospace">sentry</span> at address '
              '<a href="{website}">{website}</a>, on which you can create an '
              'account to help.\n\nGet in touch if you want to send errors to '
              'your own <span face="monospace">sentry</span>.'
              '</span>').format(website=gpod('sentry_url')),
            self.on_switch_activated,
            gpod('use_sentry'),
            func_args=('use_sentry', ),
            label_options={'line_wrap': True},
        )

        pg.attach_next_to(
            self.lbl_use_sentry,
            self.lbl_remember_windows_states,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pg.attach_next_to(
            self.swi_use_sentry,
            self.lbl_use_sentry,
            Gtk.PositionType.RIGHT,
            1, 1)

        if not sentry.usable:
            self.swi_use_sentry.set_sensitive(False)

        # ————————————————————————————————————————————— Use treeview tooltips

        (self.lbl_treeview_show_tooltips,
         self.swi_treeview_show_tooltips) = build_label_and_switch(
            _('<b>Display tooltips in main view</b>\n'
              '<span foreground="grey" size="small">'
              'Show bibliographic entries preview as you hover them with '
              'your mouse cursor. Use <span face="monospace">Shift-Control-T'
              '</span> to toggle this setting while in the main view.</span>'),
            self.on_switch_activated,
            gpod('treeview_show_tooltips'),
            func_args=('treeview_show_tooltips', ),
            label_options={'line_wrap': True},
        )

        pg.attach_next_to(
            self.lbl_treeview_show_tooltips,
            self.lbl_use_sentry,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pg.attach_next_to(
            self.swi_treeview_show_tooltips,
            self.lbl_treeview_show_tooltips,
            Gtk.PositionType.RIGHT,
            1, 1)

        # ————————————————————————————————————————————— Use treeview background

        (self.lbl_use_treeview_background,
         self.swi_use_treeview_background) = build_label_and_switch(
            _('<b>Use Bibed backgrounds</b>\n'
              '<span foreground="grey" size="small">'
              'Display light background in the main table view.\n'
              'Use <span face="monospace">Shift-Control-R</span> to '
              'randomly cycle backgrounds.</span>'),
            self.on_switch_activated,
            gpod('use_treeview_background'),
            func_args=('use_treeview_background', ),
            label_options={'line_wrap': True},
        )

        pg.attach_next_to(
            self.lbl_use_treeview_background,
            self.lbl_treeview_show_tooltips,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pg.attach_next_to(
            self.swi_use_treeview_background,
            self.lbl_use_treeview_background,
            Gtk.PositionType.RIGHT,
            1, 1)

        # ———————————————————————————————————————————————————— End widgets

        self.page_general = pg

        self.notebook.append_page(
            in_scrolled(self.page_general),
            vbox_with_icon_and_label(
                'general',
                _('General'),
                icon_name='preferences-system-symbolic',
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
            _('<b>Single selection copy to clipboard</b>\n'
              '<span size="small" color="grey">'
              'When you select only one entry in the list.</span>'),
            line_wrap=True),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER,
        )

        self.lbl_copy_single_help = widget_properties(label_with_markup(
            _('<span size="small"><span color="grey">'
              'Type any other pattern to create your own, using '
              '<span color="lightgrey"><tt>@@key@@</tt></span> '
              'anywhere inside.</span>\n'
              '<span color="red">WARNING: </span>'
              '<span color="grey">any error in your pattern will '
              'make it replaced with application default, '
              'aka <span color="lightgrey"><tt>{default}</tt></span>.'
              '</span></span>').format(default=defsigval),
            line_wrap=True),
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

        # ———————————————————————————————————————————— Remember open files

        (self.lbl_url_action_opens_browser,
         self.swi_url_action_opens_browser) = build_label_and_switch(
            _('<b>URLs open in browser</b>\n'
              '<span foreground="grey" size="small">'
              'Enabling this makes <span face="monospace">Control-U</span> '
              'and URL-icon click open the url directly '
              'in a new tab of your prefered web browser, while <span '
              'face="monospace">Shift-Control-U</span> will '
              'copy the URL to clipboard. Disabling it makes the '
              'opposite.</span>'),
            self.on_switch_activated,
            gpod('url_action_opens_browser'),
            func_args=('url_action_opens_browser', ),
            label_options={'line_wrap': True},
        )

        pa.attach_next_to(
            self.lbl_url_action_opens_browser,
            self.lbl_copy_single_help,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pa.attach_next_to(
            self.swi_url_action_opens_browser,
            self.lbl_url_action_opens_browser,
            Gtk.PositionType.RIGHT,
            1, 1)

        # ———————————————————————————————————————————————————— End widgets

        self.page_accels = pa

        self.notebook.append_page(
            self.page_accels,
            vbox_with_icon_and_label(
                'accelerators',
                _('Accelerators'),
                icon_name='preferences-desktop-keyboard-shortcuts-symbolic',
            )
        )

    def setup_page_creator_editor(self):

        pce = grid_with_common_params()

        # —————————————————————————————————————————————————— BIB auto save

        (self.lbl_bib_add_timestamp,
         self.swi_bib_add_timestamp) = build_label_and_switch(
            _('<b>Add creation timestamp</b>\n'
              '<span foreground="grey" size="small">'
              'When adding a new bibliographic entry to database, '
              'stamp it with the date of today in the '
              '<span face="monospace">timestamp</span> field.</span>'),
            self.on_switch_activated,
            gpod('bib_add_timestamp'),
            func_args=('bib_add_timestamp', ),
            label_options={'line_wrap': True},
        )

        pce.attach(
            self.lbl_bib_add_timestamp,
            # left, top, width, height
            0, 0, 1, 1)

        pce.attach_next_to(
            self.swi_bib_add_timestamp,
            self.lbl_bib_add_timestamp,
            Gtk.PositionType.RIGHT,
            1, 1)

        (self.lbl_bib_update_timestamp,
         self.swi_bib_update_timestamp) = build_label_and_switch(
            _('<b>Update timestamp on change</b>\n'
              '<span foreground="grey" size="small">'
              'When modifiying a bibliographic entry, update '
              '<span face="monospace">timestamp</span>.</span>'),
            self.on_switch_activated,
            gpod('bib_update_timestamp'),
            func_args=('bib_update_timestamp', ),
            label_options={'line_wrap': True},
        )

        pce.attach_next_to(
            self.lbl_bib_update_timestamp,
            self.lbl_bib_add_timestamp,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pce.attach_next_to(
            self.swi_bib_update_timestamp,
            self.lbl_bib_update_timestamp,
            Gtk.PositionType.RIGHT,
            1, 1)

        # ——————————————————————————————————————————————————————— bib add owner

        (self.lbl_bib_add_owner,
         self.swi_bib_add_owner) = build_label_and_switch(
            _('<b>Add owner at creation</b>\n'
              '<span foreground="grey" size="small">'
              'When creating a bibliographic entry, automatically add '
              'an <span face="monospace">owner</span> field. '
              'You have to specify a name in the field below, else nothing '
              'will be added.</span>'),
            self.on_switch_activated,
            gpod('bib_add_owner'),
            func_args=('bib_add_owner', ),
            label_options={'line_wrap': True},
        )

        pce.attach_next_to(
            self.lbl_bib_add_owner,
            self.lbl_bib_update_timestamp,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pce.attach_next_to(
            self.swi_bib_add_owner,
            self.lbl_bib_add_owner,
            Gtk.PositionType.RIGHT,
            1, 1)

        # ———————————————————————————————————————————————————— bib update owner

        (self.lbl_bib_update_owner,
         self.swi_bib_update_owner) = build_label_and_switch(
            _('<b>Update owner on change</b>\n'
              '<span foreground="grey" size="small">'
              'When changing a bibliographic entry that was not created '
              'by you, overwrite the previous <span face="monospace">'
              'owner</span> with you own value.</span>'),
            self.on_switch_activated,
            gpod('bib_update_owner'),
            func_args=('bib_update_owner', ),
            label_options={'line_wrap': True},
        )

        pce.attach_next_to(
            self.lbl_bib_update_owner,
            self.lbl_bib_add_owner,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pce.attach_next_to(
            self.swi_bib_update_owner,
            self.lbl_bib_update_owner,
            Gtk.PositionType.RIGHT,
            1, 1)
        # —————————————————————————————————————————————————————— bib owner name

        # TODO: build a ComboBox for that ? With unix username by default.

        (self.lbl_bib_owner_name,
         self.etr_bib_owner_name) = build_entry_field_labelled_entry(
            # doc. HACK: using an empty text, nothing will be shown.
            '',

            # label
            _('<b>Owner name</b>\n'
              '<span foreground="grey" size="small">'
              'Can be one or more words, including an email address.\n'
              'Valid characters include <span face="monospace">[a-z]</span>, '
              '<span face="monospace">[0-9]</span> and “<span '
              'face="monospace">-</span>”, “<span '
              'face="monospace">__</span>”, “<span '
              'face="monospace">@</span>” and “<span '
              'face="monospace">:</span>”.</span>'),

            # Field name.
            'bib_owner_name',

            # entry. We use None becaure we are not in entry editor.
            None,
            label_options={'line_wrap': True},
        )

        self.etr_bib_owner_name.set_text(preferences.bib_owner_name)

        self.etr_bib_owner_name.connect(
            'changed', self.on_etr_bib_owner_name_changed)

        pce.attach_next_to(
            self.lbl_bib_owner_name,
            self.lbl_bib_update_owner,
            Gtk.PositionType.BOTTOM,
            1, 1)

        pce.attach_next_to(
            self.etr_bib_owner_name,
            self.lbl_bib_owner_name,
            Gtk.PositionType.RIGHT,
            1, 1)

        # ———————————————————————————————————————————————————— End widgets

        self.page_creator = pce

        self.notebook.append_page(
            self.page_creator,
            vbox_with_icon_and_label(
                'creator_editor',
                _('Creator / Editor'),
                icon_name='bookmark-new-symbolic',
            )
        )

    def setup_page_interface_customization(self):

        def build_dnd(qualify, title):

            defl_main  = defaults.types.main
            defl_other = defaults.types.other
            pref_main  = preferences.types.main
            pref_other = preferences.types.other

            if qualify == 'main':
                children = defl_main if pref_main is None else pref_main
                min_max_children_per_line = (2, 3)

            else:
                children = defl_other if pref_other is None else pref_other
                # dnd_area.drag_source_set_icon_name(Gtk.STOCK_GO_BACK)
                min_max_children_per_line = (1, 2)

            (frame, scrolled, dnd_area) = dnd_scrolled_flowbox(
                name=qualify, title=title, dialog=self,
                child_type='type', child_widget='icon'
                if qualify == 'main' else 'simple',
                connect_to=self.on_flowbox_type_item_activated,
                min_max=min_max_children_per_line)

            dnd_area.add_items(children)

            return (frame, scrolled, dnd_area)

        pic = grid_with_common_params()  # column_homogeneous=True

        (self.fr_creator_dnd_main,
         self.sw_creator_dnd_main,
         self.fb_creator_dnd_main) = build_dnd(
            'main',
            # NOTE: spaces and non-breaking spaces are important.
            _('   Main types   ')
        )
        (self.fr_creator_dnd_other,
         self.sw_creator_dnd_other,
         self.fb_creator_dnd_other) = build_dnd(
            'other',
            # NOTE: spaces and non-breaking spaces are important.
            _('   Other types   ')
        )

        self.lbl_creator = widget_properties(label_with_markup(
            _('<big>Main and other entry types</big>\n'
              '<span foreground="grey">'
              'Drag and drop items from one side to another '
              'to have</span> main <span foreground="grey">'
              'items displayed first in entry '
              'creator assistant, and</span> other '
              '<span foreground="grey">accessible '
              'in a folded area of the assistant.\n\n'
              'Note: they will appear in the exact order '
              'you organize them into.</span>'),
            line_wrap=True),
            expand=False,
            halign=Gtk.Align.START,
            valign=Gtk.Align.START)

        self.btn_creator_reset = widget_properties(
            # edit-clear-all-symbolic

            Gtk.Button(_('Reset to defaults')),
            expand=False,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.END,
            margin_top=GRID_ROWS_SPACING,
            margin_bottom=GRID_ROWS_SPACING)

        self.btn_creator_reset.connect('clicked', self.on_creator_reset)

        self.btn_creator_reset.set_sensitive(
            bool(preferences.types.main and preferences.types.main != defaults.types.main) or bool(preferences.types.other and preferences.types.other != defaults.types.other)
        )

        # debug_widget(self.lbl_creator)
        pic.attach(
            self.lbl_creator,
            0, 0, 1, 1
        )

        pic.attach_next_to(
            self.btn_creator_reset,
            self.lbl_creator,
            Gtk.PositionType.BOTTOM,
            1, 1
        )

        pic.attach_next_to(
            self.fr_creator_dnd_main,
            self.lbl_creator,
            Gtk.PositionType.RIGHT,
            1, 2
        )

        pic.attach_next_to(
            self.fr_creator_dnd_other,
            self.fr_creator_dnd_main,
            Gtk.PositionType.RIGHT,
            1, 2
        )

        self.page_interface_customization = pic

        self.notebook.append_page(
            self.page_interface_customization,
            vbox_with_icon_and_label(
                'interface_customization',
                _('Interface customization'),
                icon_name='preferences-desktop-screensaver-symbolic',
            )
        )

    def setup_finish(self):

        self.on_bib_add_timestamp_activated(
            self.swi_bib_add_timestamp.get_active()
        )
        self.on_bib_add_owner_activated(
            self.swi_bib_add_owner.get_active()
        )

    # ———————————————————————————————————————————————————————————— Gtk & Signal

    def run(self):

        result = super().run()

        # This operation cannot be done while user is typing new accels,
        # else every char-typing is saved as a new entry, which makes a
        # lot of false positives.
        self.save_accelerators()

        return result

    def on_working_folder_set(self, widget):

        new_folder = self.fcb_working_folder.get_filename()

        if new_folder != preferences.working_folder:

            LOGGER.info(
                'on_working_folder_changed(): set to {}'.format(new_folder))

            preferences.working_folder = new_folder

    def on_books_folder_set(self, widget):

        new_folder = self.fcb_books_folder.get_filename()

        if new_folder != preferences.books_folder:

            LOGGER.info(
                'on_books_folder_changed(): set to {}'.format(new_folder))

            preferences.books_folder = new_folder

    def on_switch_activated(self, switch, gparam, preference_name):

        is_active = switch.get_active()

        # We need to test, else the set_active() call in dialog
        # constructor triggers a superflous preferences save().
        if getattr(preferences, preference_name) != is_active:
            setattr(preferences, preference_name, is_active)

        post_change_method = getattr(
            self, 'on_{}_activated'.format(preference_name), None)

        if post_change_method:
            try:
                post_change_method(is_active)

            except AttributeError:
                # When building the preferences window,
                # Not all fields are present (order of
                # construction matters).
                pass

    def on_use_sentry_activated(self, is_active):

        if is_active:
            sentry.enable()

        else:
            sentry.disable()

    def on_treeview_show_tooltips_activated(self, is_active):

        controllers.application.window.treeview.switch_tooltips(is_active)

    def on_use_treeview_background_activated(self, is_active):

        # Reload the whole application CSS, to enable or disable background.
        controllers.application.reload_css_provider_data()

    def on_bib_add_timestamp_activated(self, is_active):

        if is_active:
            self.swi_bib_update_timestamp.set_sensitive(True)

        else:
            self.swi_bib_update_timestamp.set_sensitive(False)

    def on_bib_add_owner_activated(self, is_active):

        if is_active:
            self.swi_bib_update_owner.set_sensitive(True)
            self.etr_bib_owner_name.set_sensitive(True)

            if not self.etr_bib_owner_name.get_text().strip():
                add_classes(self.etr_bib_owner_name, ['error'])

        else:
            remove_classes(self.etr_bib_owner_name, ['error'])

            self.swi_bib_update_owner.set_sensitive(False)
            self.etr_bib_owner_name.set_sensitive(False)

    def on_spin_keep_recent_files_changed(self, adj):

        value = int(adj.get_value())

        if preferences.keep_recent_files is None:
            preferences.keep_recent_files = value

        else:
            # Need to test to avoid double (and useless) save().
            if preferences.keep_recent_files != value:
                preferences.keep_recent_files = value

    def on_combo_single_copy_changed(self, combo):

        # Note: see self.run()

        option = combo.get_active_text()

        preferences.accelerators.copy_to_clipboard_single_value = option
        preferences.save()

    def on_etr_bib_owner_name_changed(self, entry):

        # Note: see self.run()

        value = entry.get_text()

        if OWNER_NAME_RE.match(value) is None:
            add_classes(entry, ['error'])
        else:
            remove_classes(entry, ['error'])

            # Auto-save on setter…
            preferences.bib_owner_name = value

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

    def on_flowbox_type_item_activated(self, flowbox, flowchild, *args, **kwargs):

        print('GO', flowbox.get_name(), '→', flowchild.get_child().get_name())

    # ———————————————————————————————————————————————————— Types fields editor

    def setup_page_editor_fields(self):

        pass

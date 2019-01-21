
import math
import string
import logging

from bibed.constants import (
    APP_NAME,
    JABREF_READ_KEYWORDS,
    JABREF_QUALITY_KEYWORDS,
    BOXES_BORDER_WIDTH,
    GRID_COLS_SPACING,
    GRID_ROWS_SPACING,
    GRID_BORDER_WIDTH,
    PANGO_BIG_FONT_SIZES,
)

from bibed.preferences import defaults, preferences
from bibed.uihelpers import (
    widget_properties,
    label_with_markup,
)
from bibed.gtk import Gtk

LOGGER = logging.getLogger(__name__)


# ———————————————————————————————————————————————————————————————— Functions


def entry_get_keywords(entry):
    ''' Return entry keywords without JabRef internals. '''

    keywords = entry.fields.get('keywords', [])

    for kw in JABREF_QUALITY_KEYWORDS + JABREF_READ_KEYWORDS:
        try:
            keywords.remove(kw)
        except ValueError:
            pass

    return keywords


def entry_get_quality(entry):
    ''' Get the JabRef quality from keywords. '''

    keywords = entry.fields.get('keywords', '').split(',')

    for kw in JABREF_QUALITY_KEYWORDS:
        if kw in keywords:
            return kw

    return ''


def entry_get_read_status(entry):
    ''' Get the JabRef read status from keywords. '''

    keywords = entry.fields.get('keywords', '').split(',')

    for kw in JABREF_READ_KEYWORDS:
        if kw in keywords:
            return kw

    return ''


def bib_entry_format_author_pybtex(persons):

    if persons is None:
        return '—'

    pstring = ''
    local_pstring = ''

    for p in persons:
        local_pstring = '{0} {1} {2} {3}'.format(
            p.first_names[0] if p.first_names else '',
            p.middle_names[0] if p.middle_names else '',
            p.prelast_names[0] if p.prelast_names else '',
            p.last_names[0] if p.last_names else '')

        local_pstring = local_pstring.strip()

        if local_pstring.startswith('{'):
            local_pstring = local_pstring[1:-1]

        pstring += local_pstring + ', '

    while '  ' in pstring:
        pstring = pstring.replace('  ', ' ')

    if pstring.endswith(', '):
        pstring = pstring[:-2]

    return pstring


def bib_entry_format_journal_pybtex(journal):

    if journal == '':
        return ''

    if journal.startswith('{'):
        journal = journal[1:-1]

    journal = journal.replace('\\&', '&')

    return journal


bib_entry_format_author = bib_entry_format_author_pybtex
bib_entry_format_journal = bib_entry_format_journal_pybtex


def bib_entry_to_store_row_list_pybtex(global_counter, origin, counter, entry):
    ''' Get a BIB entry, and get displayable fields for Gtk List Store. '''

    fields = entry.fields
    persons = entry.persons

    return [
        global_counter,
        origin,
        counter,
        entry.type,
        entry.key,
        fields.get('file', ''),
        fields.get('url', ''),
        fields.get('doi', ''),
        bib_entry_format_author(persons.get('author', None)),
        fields.get('title', ''),
        bib_entry_format_journal(fields.get('journal', '')),
        int(fields.get('year', fields.get('date', '0').split('-')[0])),
        fields.get('date', ''),
        entry_get_quality(entry),
        entry_get_read_status(entry),
    ]


bib_entry_to_store_row_list = bib_entry_to_store_row_list_pybtex


def single_bibkey_to_copy_check(pattern):

    if '@@key@@' in pattern:
        return pattern

    else:
        return defaults.accelerators.copy_to_clipboard_single_value


def format_single_bibkey_to_copy(bib_key):

    defls = defaults.accelerators.copy_to_clipboard_single_value
    prefs = preferences.accelerators.copy_to_clipboard_single_value

    if prefs is None:
        pattern = defls

    else:
        pattern = prefs

    pattern = single_bibkey_to_copy_check(pattern)

    result = pattern.replace('@@key@@', bib_key)

    return result


# —————————————————————————————————————————————————————————————————— Classes

class BibedEntryTypeDialog(Gtk.Dialog):

    def __init__(self, parent, add_new=False):
        Gtk.Dialog.__init__(
            self, "{0} — new entry".format(APP_NAME), parent, 0)

        self.set_modal(True)
        self.set_default_size(500, 300)
        self.set_border_width(BOXES_BORDER_WIDTH)

        self.box = self.get_content_area()

        self.setup_stack()

        self.box.add(widget_properties(label_with_markup(
            '<span foreground="grey">Keep keyboard key <span '
            'face="monospace">Alt</span> pressed to show mnemonics, '
            'available on most bibliographic entry types.'
            '</span>'.format(APP_NAME),
            xalign=0.5),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.CENTER,
            margin_top=5))

        self.box.add(widget_properties(label_with_markup(
            '<span foreground="grey">Hover types marked with <span '
            'face="monospace">(?)</span> with your mouse '
            ' for a moment to show type description.'
            '</span>',
            xalign=0.5),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.CENTER,
            margin_top=5))

        self.show_all()

    def setup_stack(self):

        def build_types_grid(qualify, children, btn_markup, size, size_multiplier):

            grid = Gtk.Grid()
            grid.set_border_width(BOXES_BORDER_WIDTH * size_multiplier)
            grid.set_column_spacing(GRID_COLS_SPACING * size_multiplier)
            grid.set_row_spacing(GRID_ROWS_SPACING * size_multiplier)

            mnemonics = defaults.types.mnemonics

            divider = round(math.sqrt(len(children)))
            if divider > 4:
                divider = 4
            row_index = 0

            for index, child_name in enumerate(children):

                label = widget_properties(
                    Gtk.Label(),
                    expand=False,
                    margin=BOXES_BORDER_WIDTH * size_multiplier,
                    halign=Gtk.Align.CENTER,
                    valign=Gtk.Align.CENTER,
                )

                field_node = getattr(defaults.fields, child_name)
                field_has_help = (
                    field_node is not None and field_node.doc is not None
                )

                label.set_markup_with_mnemonic(
                    btn_markup.format(
                        size=size, label=mnemonics[child_name],
                        help='<span color="grey"><sup><small>(?)</small></sup></span>'
                        if field_has_help else ''))

                btn = widget_properties(
                    Gtk.Button(),
                    expand=False,
                    # margin=BOXES_BORDER_WIDTH,
                    halign=Gtk.Align.CENTER,
                    valign=Gtk.Align.CENTER,
                )
                btn.add(label)
                btn.set_relief(Gtk.ReliefStyle.NONE)
                label.set_mnemonic_widget(btn)
                btn.connect('clicked', self.on_type_clicked, child_name)

                if field_has_help:
                        btn.set_tooltip_markup(field_node.doc)

                grid.attach(
                    btn,
                    int(index % divider),
                    row_index,
                    1, 1
                )

                if index % divider + 1 == divider:
                    row_index += 1

            return grid

        stack = Gtk.Stack()

        # stack.set_transition_type(
        #     Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        # stack.set_transition_duration(500)

        if preferences.types.main is None:
            types_main = defaults.types.main
            types_other = defaults.types.other

        else:
            types_main = preferences.types.main
            types_other = preferences.types.other

        len_fonts = len(PANGO_BIG_FONT_SIZES)
        len_other = len(types_other)
        len_main  = len(types_main)

        if len_other > len_main:
            size_multiplier  = int(len_other / len_main)
            size_mult_main   = size_multiplier
            size_mult_other  = 1
            label_tmpl_main  = '<span size="{size}">{label}</span>{help}'
            label_tmpl_other = '{label}{help}'
        else:
            size_multiplier  = int(len_main / len_other)
            size_mult_main   = 1
            size_mult_other  = size_multiplier
            label_tmpl_main  = '{label}{help}'
            label_tmpl_other = '<span size="{size}">{label}</span>{help}'

        if size_multiplier > len_fonts:
            size_multiplier = len_fonts

        font_size = PANGO_BIG_FONT_SIZES[size_multiplier]

        self.grid_types_main = build_types_grid(
            'main', types_main, label_tmpl_main, font_size, size_mult_main
        )
        self.grid_types_other = build_types_grid(
            'other', types_other, label_tmpl_other, font_size, size_mult_other
        )

        stack_switcher = widget_properties(
            Gtk.StackSwitcher(),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            margin=GRID_BORDER_WIDTH * size_multiplier,
        )

        stack_switcher.set_stack(stack)

        if preferences.types.main is None:
            main_stack_label = "{}'s main types".format(APP_NAME)
            other_stack_label = "Other bibliographic types"

        else:
            main_stack_label = "Your main types"
            other_stack_label = "Other types"

        stack.add_titled(
            self.grid_types_main,
            "main",
            main_stack_label,
        )

        stack.add_titled(
            self.grid_types_other,
            "other",
            other_stack_label,
        )

        self.stack_switcher = stack_switcher
        self.stack = stack

        self.box.add(self.stack_switcher)
        self.box.add(self.stack)

    def get_entry(self):

        return self.entry

    def on_type_clicked(self, button, entry_type):

        # TODO: convert to entry bibtexparser
        self.entry = entry_type

        self.response(Gtk.ResponseType.OK)


class BibedEntryDialog(Gtk.Dialog):

    @property
    def auto_save(self):
        return preferences.auto_save or (
            preferences.auto_save is None and defaults.auto_save)

    def __init__(self, parent, entry):
        super().__init__(
            "{0}: edit entry “{1}”".format(APP_NAME), parent, 0)

        self.set_modal(True)
        self.set_default_size(500, 300)
        self.set_border_width(BOXES_BORDER_WIDTH)
        self.props.use_header_bar = True
        self.connect('hide', self.on_add_entry_hide)

        self.entry = entry

        self.setup_headerbar()

        box = self.get_content_area()

        if self.auto_save:
            box.add(widget_properties(label_with_markup(
                '<span foreground="grey">Entry is automatically saved; '
                'just hit <span face="monospace">ESC</span> or close '
                'the window when you are done.'
                '</span>',
                xalign=0.5),
                expand=Gtk.Orientation.HORIZONTAL,
                halign=Gtk.Align.CENTER,
                margin_top=5))

        self.show_all()

    def setup_headerbar(self):

        self.headerbar = self.get_header_bar()

        bbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        Gtk.StyleContext.add_class(bbox.get_style_context(), "linked")

        button = Gtk.Button()
        button.add(Gtk.Arrow(arrow_type=Gtk.ArrowType.LEFT,
                             shadow_type=Gtk.ShadowType.NONE))
        bbox.add(button)

        self.btn_previous = button
        self.btn_previous.connect('clicked', self.on_previous_clicked)

        button = Gtk.Button()
        button.add(Gtk.Arrow(arrow_type=Gtk.ArrowType.RIGHT,
                             shadow_type=Gtk.ShadowType.NONE))
        bbox.add(button)

        self.btn_next = button
        self.btn_next.connect('clicked', self.on_next_clicked)

    def on_add_entry_hide(self, window):

        # TODO: are you sure ? and auto save ?
        self.save_entry()

    def on_next_clicked(self, button):

        if not self.auto_save and self.needs_save:
            # display a new modal discard / save and go on
            pass

        else:
            pass

    def save_entry(self):

        LOGGER.error('IMPLEMENT {}.save_entry()')

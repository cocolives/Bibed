
import math
import logging

from bibed.constants import (
    APP_NAME,
    BOXES_BORDER_WIDTH,
    GRID_COLS_SPACING,
    GRID_ROWS_SPACING,
    GRID_BORDER_WIDTH,
    PANGO_BIG_FONT_SIZES,
    GENERIC_HELP_SYMBOL,
)

from bibed.preferences import defaults, preferences

from bibed.gui.helpers import (
    widget_properties,
    label_with_markup,
    # in_scrolled,
    # frame_defaults,
    # scrolled_textview,
)

from bibed.gui.gtk import Gtk


LOGGER = logging.getLogger(__name__)


class BibedEntryTypeDialog(Gtk.Dialog):

    def __init__(self, parent, add_new=False):
        super().__init__('Choose new entry type', parent, 0)

        self.set_modal(True)
        self.set_default_size(300, 300)
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

                type_node = getattr(defaults.fields, child_name)
                type_has_help = (
                    type_node is not None and type_node.doc is not None
                )
                type_has_fields = (
                    type_node is not None and type_node.required is not None
                )

                label.set_markup_with_mnemonic(
                    btn_markup.format(
                        size=size, label=mnemonics[child_name],
                        help=GENERIC_HELP_SYMBOL
                        if type_has_help else ''))

                btn = widget_properties(
                    Gtk.Button(),
                    expand=True,
                    margin=BOXES_BORDER_WIDTH * size_multiplier,
                    halign=Gtk.Align.CENTER,
                    valign=Gtk.Align.CENTER,
                )
                btn.add(label)
                btn.set_relief(Gtk.ReliefStyle.NONE)
                label.set_mnemonic_widget(btn)
                btn.connect('clicked', self.on_type_clicked, child_name)

                if not type_has_fields:
                    # We cannot implement edition for now.
                    btn.set_sensitive(False)

                if type_has_help:
                        btn.set_tooltip_markup(type_node.doc)

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
            size_mult_other  = 0.01
            label_tmpl_main  = '<span size="{size}">{label}</span>{help}'
            label_tmpl_other = '{label}{help}'

        else:
            size_multiplier  = int(len_main / len_other)
            size_mult_main   = 0.1
            size_mult_other  = size_multiplier
            label_tmpl_main  = '{label}{help}'
            label_tmpl_other = '<span size="{size}">{label}</span>{help}'

        if size_multiplier > len_fonts:
            size_multiplier = len_fonts

        font_size = PANGO_BIG_FONT_SIZES[size_multiplier]

        if size_multiplier > 3:
            size_multiplier = 3

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

    def get_entry_type(self):

        return self.entry_type

    def on_type_clicked(self, button, entry_type):

        # TODO: convert to entry bibtexparser
        self.entry_type = entry_type

        self.response(Gtk.ResponseType.OK)


import logging
from collections import OrderedDict

from bibed.constants import (
    BOXES_BORDER_WIDTH,
    GRID_COLS_SPACING,
    GRID_ROWS_SPACING,
    GRID_BORDER_WIDTH,
    # GENERIC_HELP_SYMBOL,
)

from bibed.preferences import defaults, preferences

from bibed.gui.helpers import (
    widget_properties,
    label_with_markup,
    in_scrolled,
    # frame_defaults,
    # scrolled_textview,
    build_entry_field_labelled_entry,
    build_entry_field_textview,
)

from bibed.gui.gtk import Gtk, Gio

LOGGER = logging.getLogger(__name__)


class BibedEntryDialog(Gtk.Dialog):

    @property
    def is_auto_save(self):
        return preferences.auto_save or (
            preferences.auto_save is None and defaults.auto_save)

    def __init__(self, parent, entry):

        if entry.key is None:
            title = "Create new @{0}".format(entry.type)
        else:
            try:
                mnemonic = getattr(defaults.fields.mnemonics,
                                   entry.type).label

            except AttributeError:
                # Poor man's solution.
                mnemonic = entry.type.title()

            title = "Edit {0} {1}".format(mnemonic, entry.key)

        super().__init__(title, parent, use_header_bar=True)

        self.set_modal(True)
        self.set_default_size(500, 500)
        self.set_border_width(BOXES_BORDER_WIDTH)
        self.connect('hide', self.on_entry_hide)

        self.entry = entry

        self.setup_headerbar()

        self.box = self.get_content_area()

        # direct access to fields for *save() methods.
        self.fields = OrderedDict()

        self.setup_key_entry()

        # Direct access to fields grids.
        self.grids = {}

        self.setup_stack()

        if self.is_auto_save:
            self.box.add(widget_properties(label_with_markup(
                '<span foreground="grey">Entry is automatically saved; '
                'just hit <span face="monospace">ESC</span> or close '
                'the window when you are done.'
                '</span>',
                xalign=0.5),
                expand=Gtk.Orientation.HORIZONTAL,
                halign=Gtk.Align.CENTER,
                margin_top=5))

        self.show_all()

        # Focus the first sensitive field
        # (eg. 'key' for new entries, 'title' for existing).
        for val in self.fields.values():
            if val.get_sensitive():
                val.grab_focus()
                break

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

        self.headerbar.pack_start(bbox)

        if self.entry.key is None:
            # We need to wait after the entry is first saved.
            bbox.set_sensitive(False)

        btn_switch_type = widget_properties(Gtk.Button(), expand=False)
        btn_switch_type.connect('clicked', self.on_switch_type_clicked)
        icon = Gio.ThemedIcon(name='network-transmit-receive-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        btn_switch_type.add(image)
        btn_switch_type.set_tooltip_markup('Switch entry type')

        self.headerbar.pack_end(btn_switch_type)

    def setup_key_entry(self):

        field_name = 'key'

        hbox = widget_properties(
            Gtk.HBox(),
            expand=False,
            halign=Gtk.Align.CENTER,
        )
        Gtk.StyleContext.add_class(hbox.get_style_context(), 'linked')

        mnemonics = defaults.fields.mnemonics

        label, entry = build_entry_field_labelled_entry(
            mnemonics, field_name, self.entry
        )

        self.fields[field_name] = entry

        # Special: align label next to entry.
        label.set_xalign(1.0)
        entry.set_size_request(250, -1)
        entry.connect('changed',
                      self.on_field_changed,
                      field_name)

        btn_rename = widget_properties(Gtk.Button(), expand=False)
        btn_rename.connect('clicked', self.on_key_rename_clicked)
        icon = Gio.ThemedIcon(name='document-edit-symbolic')
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        btn_rename.add(image)
        btn_rename.set_tooltip_markup('Rename entry key')

        if self.entry.key is None:
            btn_rename.set_sensitive(False)

        else:
            entry.set_text(self.entry.key)
            entry.set_sensitive(False)

        hbox.add(label)
        hbox.add(entry)
        hbox.add(btn_rename)

        self.box.add(hbox)

    def setup_stack(self):

        def build_fields_grid(entry, fields):

            def connect_and_attach_to_grid(label, entry, field_name):
                entry.connect('changed',
                              self.on_field_changed,
                              field_name)
                self.fields[field_name] = entry
                grid.attach(label, 0, index, 1, 1)
                grid.attach(entry, 1, index, 1, 1)

            grid = Gtk.Grid()
            grid.set_border_width(BOXES_BORDER_WIDTH)
            grid.set_column_spacing(GRID_COLS_SPACING)
            grid.set_row_spacing(GRID_ROWS_SPACING)

            mnemonics = defaults.fields.mnemonics

            if len(fields) == 1:
                field_name = fields[0]
                scr, txv = build_entry_field_textview(
                    mnemonics, field_name, entry)

                self.fields[field_name] = txv
                grid.attach(scr, 0, 0, 1, 1)

            else:
                index = 0
                for field_name in fields:
                    if isinstance(field_name, list):
                        for subfield_name in field_name:
                            connect_and_attach_to_grid(
                                *build_entry_field_labelled_entry(
                                    mnemonics, subfield_name, entry
                                ), subfield_name,
                            )
                            index += 1
                    else:
                        connect_and_attach_to_grid(
                            *build_entry_field_labelled_entry(
                                mnemonics, field_name, entry
                            ), field_name,
                        )
                        index += 1

            return grid

        stack = Gtk.Stack()

        fields_entry_node = getattr(preferences.fields, self.entry.type)

        if fields_entry_node is None:
            fields_entry_node = getattr(defaults.fields, self.entry.type)

            # HEADS UP: attributes names are different
            #       between defaults and preferences.
            fields_main = fields_entry_node.required[:]
            fields_secondary = []

            fields_other = fields_entry_node.optional[:]

            try:
                fields_stacks = fields_entry_node.stacked[:]

            except TypeError:
                fields_stacks = []

        else:
            fields_main = fields_entry_node.main[:]
            fields_secondary = fields_entry_node.secondary[:]
            fields_other = fields_entry_node.other[:]

            try:
                fields_stacks = fields_entry_node.stacks[:]

            except TypeError:
                fields_stacks = []

        for field_name in fields_stacks:
            if field_name in fields_other:
                # This can happen in defaults.
                # TODO: chek defaults to avoid it.
                fields_other.remove(field_name)

        self.grids['main'] = build_fields_grid(
            self.entry, fields_main,
        )

        if fields_secondary:
            self.grids['secondary'] = build_fields_grid(
                self.entry, fields_secondary,
            )

        for field_name in fields_stacks:
            self.grids[field_name] = build_fields_grid(
                self.entry,  # TODO: Find Mnemonic
                [field_name],
            )

        self.grids['other'] = build_fields_grid(
            self.entry, fields_other,
        )

        stack_switcher = widget_properties(
            Gtk.StackSwitcher(),
            expand=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            margin=GRID_BORDER_WIDTH,
        )

        stack_switcher.set_stack(stack)

        if preferences.types.main is None:
            main_stack_label = "Required fields"
            other_stack_label = "Optional fields"

        else:
            main_stack_label = "Main fields"
            secondary_stack_label = "Secondary fields"
            other_stack_label = "Other fields"

        stack.add_titled(
            in_scrolled(self.grids['main']),
            'main',
            main_stack_label,
        )

        if fields_secondary:
            stack.add_titled(
                in_scrolled(self.grids['secondary']),
                'secondary',
                secondary_stack_label,
            )

        stack.add_titled(
            in_scrolled(self.grids['other']),
            'other',
            other_stack_label,
        )

        for grid_name, grid in self.grids.items():
            if grid_name in ['main', 'secondary', 'other']:
                continue

            stack.add_titled(
                grid,
                grid_name,
                grid_name.title(),  # TODO: find mnemonic
            )

        self.stack_switcher = stack_switcher
        self.stack = stack

        self.box.add(self.stack_switcher)
        self.box.add(self.stack)

    def on_entry_hide(self, window):

        # TODO: are you sure ? and auto save ?
        self.save_entry()

    def on_key_rename_clicked(self, button):

        LOGGER.info('Key rename clicked')

    def on_switch_type_clicked(self, button):

        LOGGER.info('Switch type clicked')

    def on_previous_clicked(self, button):

        if not self.is_auto_save and self.needs_save:
            # display a new modal discard / save and go on
            pass

        else:
            pass

    def on_next_clicked(self, button):

        if not self.is_auto_save and self.needs_save:
            # display a new modal discard / save and go on
            pass

        else:
            pass

    def on_field_changed(self, entry, field_name):

        LOGGER.info('Field {} changed to “{}”.'.format(
            field_name, entry.get_text()))

    def save_entry(self):

        LOGGER.error('IMPLEMENT {}.save_entry()')


import logging

from bibed.ltrace import (  # NOQA
    ldebug, lprint,
    lprint_caller_name,
    lprint_function_name,
)

from bibed.constants import (
    BOXES_BORDER_WIDTH,
)

# from bibed.preferences import defaults, preferences, memories, gpod

from bibed.gui.helpers import (
    add_classes,
    markup_entries,
    markup_bib_filename,
    label_with_markup,
    widget_properties,
)

from bibed.controllers import controllers
from bibed.gtk import Gtk

LOGGER = logging.getLogger(__name__)


class BibedMoveDialog(Gtk.MessageDialog):

    def __init__(self, window, selected_entries, *args, **kwargs):
        super().__init__(
            window, 0,
            Gtk.MessageType.QUESTION,
            Gtk.ButtonsType.OK_CANCEL,
        )

        self.set_default_response(Gtk.ResponseType.OK)
        add_classes(
            self.get_widget_for_response(Gtk.ResponseType.OK),
            ['suggested-action'],
        )

        self.entries = selected_entries

        # Used during self operations and returned at the end.
        self.destination_database = None
        self.unchanged_count = 0
        self.moved_count = 0

        self.setup_title_and_message()
        self.setup_destinations()

    def setup_title_and_message(self):

        entries = self.entries
        entries_count = len(entries)

        if entries_count > 1:
            title = 'Move {count} entries?'.format(
                count=entries_count)

            secondary_text = (
                'Please choose a destination for the following entries:\n'
                '{entries_list}\n'.format(
                    entries_list=markup_entries(
                        entries, entries_count, 3)))

        else:
            entry = entries[0]
            title = 'Move entry?'
            secondary_text = ('Please choose a destination for {entry}.'.format(
                entry=entry.short_display))

        self.set_markup('<big><b>{}</b></big>'.format(title))
        self.format_secondary_markup(secondary_text)

    def setup_destinations(self):

        first_database = self.entries[0].database

        radios_box = widget_properties(
            Gtk.VBox(),
            expand=False,
            halign=Gtk.Align.CENTER,
        )

        first_button = None

        for database in controllers.files.user_databases:

            filename_markup = markup_bib_filename(
                database.filename, database.filetype,
                same_line=True, same_size=False, big_size=True)

            if first_button is None:
                first_button = button = \
                    Gtk.RadioButton.new(None)

            else:
                button = Gtk.RadioButton.new_from_widget(first_button)

            button.add(widget_properties(
                label_with_markup(filename_markup, yalign=0.5),
                margin=BOXES_BORDER_WIDTH,
            ))

            button.connect('toggled',
                           self.on_destination_toggled,
                           database)

            if database == first_database:
                # Select the database of the first entry
                # to signify where they come from.
                button.set_active(True)

            radios_box.add(button)

        radios_box.show_all()
        self.get_message_area().add(radios_box)

    def run(self):
        response = super().run()

        if response == Gtk.ResponseType.OK:
            self.move_entries()

        self.hide()
        self.destroy()

        return (
            self.destination_database,
            self.moved_count,
            self.unchanged_count,
        )

    def move_entries(self):

        databases_to_write = set()

        for entry in self.entries:
            if entry.database == self.destination_database:
                self.unchanged_count += 1
                continue

            # Source database is about to loose en entry,
            # It needs a save() after the operation.
            databases_to_write.add(entry.database)

            self.destination_database.move_entry(
                # We do not write at at each move, this will
                # be done once and for all at end of operation.
                entry, self.destination_database, write=False)

            self.moved_count += 1

        if self.moved_count:
            databases_to_write.add(self.destination_database)

        for database in databases_to_write:
            database.write()

    def on_destination_toggled(self, button, destination, *args):

        if button.get_active():
            self.destination_database = destination

            LOGGER.debug('Move destination set to “{}”.'.format(destination))


import logging
import threading

from bibed.constants import BibAttrs
from bibed.parallel import run_in_background
from bibed.strings import lowunaccent
from bibed.gtk import Gtk


LOGGER = logging.getLogger(__name__)

MINIMUM_KEY_LENGTH = 2


class DeduplicateCompletion(Gtk.EntryCompletion):

    def __init__(self, field, field_name, store, column):

        super().__init__()

        self.valid_completions = {}
        self.field_name = field_name
        self.column = column
        self.minimum_key_length = 2

        self.set_model(store)
        self.set_inline_selection(True)
        self.set_text_column(column)
        self.set_minimum_key_length(self.minimum_key_length)
        self.set_match_func(self.match_func, field_name, store, column)

        field.connect('changed', self.on_entry_changed)

    def on_entry_changed(self, entry, *args):

        if len(entry.get_text()) >= self.minimum_key_length:

            # reset valid completion, because completion key changed.
            self.valid_completions = {}
            self.completion_key = entry.get_text()

            self.set_cell_data_func(self.get_cells()[0], self.cell_data_func)

    def match_func(self, widget, key, iter, field_name, store, column):
        ''' Deduplicate matched values, and match them more fuzzily. '''

        column_value = store[iter][column]
        entry_key = store[iter][BibAttrs.KEY]

        # TODO: remove completions from trashed items?

        if key.lower() in column_value.lower():

            kept_key = self.valid_completions.get(column_value, None)

            # We already got that one.
            if kept_key:
                if kept_key == entry_key:
                    return True

                return False

            self.valid_completions[column_value] = entry_key

            return True

        return False

    def cell_data_func(self, layout, cell, model, iter, *data):

        key = self.completion_key
        value = model.get_value(iter, self.column)

        start_index = value.lower().find(key)
        key_length = len(key)

        cell.set_property(
            'markup',
            '{}<b><u>{}</u></b>{}'.format(
                value[:start_index],
                value[start_index:start_index + key_length],
                value[start_index + key_length:],
            )
        )


class DeferredCompletion(Gtk.EntryCompletion):
    ''' Has to be subclassed to implement the store load method. '''

    def __init__(self, field):

        super().__init__()

        self.store = Gtk.ListStore(str)
        self.completion_key = None

        self.set_model(self.store)
        self.set_text_column(0)
        self.set_inline_completion(True)
        self.set_inline_selection(True)
        self.set_popup_set_width(True)
        self.set_minimum_key_length(MINIMUM_KEY_LENGTH)
        self.set_match_func(self.match_func, self.store)

        self.populating = False
        self.populated = threading.Event()

        field.connect('focus-in-event', self.on_field_focus)
        field.connect('changed', self.on_field_changed)

    def on_field_focus(self, field, *args):

        if self.populating:
            return

        LOGGER.debug('{}: backgrounding populate_data_store().')

        self.populating = True

        run_in_background(self.populate_data_store, self.populated)

        self.set_cell_data_func(self.get_cells()[0], self.cell_data_func)

    def on_field_changed(self, entry, *args):

        if len(entry.get_text()) >= MINIMUM_KEY_LENGTH:
            self.completion_key = entry.get_text()

    def match_func(self, widget, key, iter, store):
        ''' Deduplicate matched values, and match them more fuzzily. '''

        self.populated.wait()

        print(
            'KEY', lowunaccent(key, normalized=True), type(key),
            'MY', lowunaccent(self.completion_key), type(self.completion_key),
            'IN', lowunaccent(store[iter][0])
        )

        if lowunaccent(key, normalized=True) in lowunaccent(store[iter][0]):
            return True

        return False

    def cell_data_func(self, layout, cell, model, iter, *data):

        key = lowunaccent(self.completion_key, normalized=True)
        value = model.get_value(iter, 0)

        start_index = lowunaccent(value, normalized=True).find(key)
        end_index = start_index + len(key)

        cell.set_property(
            'markup',
            '{}<b><u>{}</u></b>{}'.format(
                value[:start_index],
                value[start_index:end_index],
                value[end_index:],
            )
        )


class DeduplicatedStoreColumnCompletion(DeferredCompletion):

    def __init__(self, field, store, column):

        super().__init__(field)

        self.source_store = store
        self.source_column = column

    def populate_data_store(self):

        source_column = self.source_column
        my_store = self.store

        for row in self.source_store:

            if row[source_column].strip() == '':
                continue

            discard_row = False

            for my_row in my_store:
                if row[source_column] == my_row[0]:
                    discard_row = True
                    break

            if discard_row:
                continue

            my_store.append((row[source_column], ))

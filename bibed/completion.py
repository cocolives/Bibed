
from bibed.constants import BibAttrs
from bibed.gtk import Gtk


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

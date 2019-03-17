
import os
import re
import logging
import datetime

from bibed.constants import (
    BibAttrs,
)
from bibed.controllers import controllers
from bibed.gtk import Gtk
from bibed.completion import (
    DeduplicatedStoreColumnCompletion,
)
from bibed.entry import generate_new_key


LOGGER = logging.getLogger(__name__)


# ————————————————————————————————————————————————————————— Regular expressions


KEY_RE = re.compile('^[a-z]([-:_a-z0-9]){2,}$', re.IGNORECASE)


# ————————————————————————————————————————————————————————————————————— Classes


class FieldUtils:

    @staticmethod
    def value_is_empty(field_value):

        return field_value is None or len(field_value.strip()) == 0

    @staticmethod
    def field_make_empty(field):

        return FieldUtils.field_set_value(field, '')

    @staticmethod
    def field_set_date_today(field):

        today_value = datetime.date.today().isoformat()

        current_date = FieldUtils.field_get_value(field)

        if current_date == today_value:
            return

        FieldUtils.field_set_value(field, today_value)

    @staticmethod
    def field_get_value(field):

        if isinstance(field, Gtk.Entry):
            return field.get_text()

        elif isinstance(field, Gtk.TextView):
            buffer = field.get_buffer()
            return buffer.get_text(
                buffer.get_start_iter(),
                buffer.get_end_iter(),
                False,
            )

        raise NotImplementedError('Unhandled field {}'.format(field))

    @staticmethod
    def field_set_value(field, value):

        assert isinstance(field, Gtk.Widget)

        if isinstance(field, Gtk.Entry):
            return field.set_text(value)

        elif isinstance(field, Gtk.TextView):
            buffer = field.get_buffer()

            return buffer.set_text(value)

        raise NotImplementedError('Unhandled field {}'.format(field))


class EntryFieldBuildMixin:
    ''' Helpers for field building. '''

    def build_field_author_post(self, all_fields, field_name, field, store):

        field.set_completion(DeduplicatedStoreColumnCompletion(
            field, store, BibAttrs.AUTHOR))

    def build_field_journaltitle_post(self, all_fields, field_name, field, store):

        field.set_completion(DeduplicatedStoreColumnCompletion(
            field, store, BibAttrs.JOURNALTITLE))

    def build_field_editor_post(self, all_fields, field_name, field, store):

        field.set_completion(DeduplicatedStoreColumnCompletion(
            field, store, BibAttrs.EDITOR))

    def build_field_publisher_post(self, all_fields, field_name, field, store):

        field.set_completion(DeduplicatedStoreColumnCompletion(
            field, store, BibAttrs.PUBLISHER))

    def build_field_series_post(self, all_fields, field_name, field, store):

        field.set_completion(DeduplicatedStoreColumnCompletion(
            field, store, BibAttrs.SERIES))

    def build_field_type_post(self, all_fields, field_name, field, store):

        field.set_completion(DeduplicatedStoreColumnCompletion(
            field, store, BibAttrs.TYPEFIELD))

    def build_field_howpublished_post(self, all_fields, field_name, field, store):

        field.set_completion(DeduplicatedStoreColumnCompletion(
            field, store, BibAttrs.HOWPUBLISHED))

    def build_field_entrysubtype_post(self, all_fields, field_name, field, store):

        field.set_completion(DeduplicatedStoreColumnCompletion(
            field, store, BibAttrs.ENTRYSUBTYPE))

    def build_field_entryset_post(self, all_fields, field_name, field, store):

        # TODO: add a custom entry key completer.

        pass

    def build_field_related_post(self, all_fields, field_name, field, store):

        # TODO: add a custom entry key completer.

        pass

    def build_field_keywords_post(self, all_fields, field_name, field, store):

        # TODO: add a custom keyword completer for a textview.

        pass


class EntryFieldCheckMixin:
    ''' This class is meant to be subclassed by any Window/Dialog that checks entries.

        .. seealso:: :class:`~bibed.gui.BibedEntryDialog`.
    '''

    # ——————————————————————————————————————————————————————————— Check methods

    def check_field_year(self, all_fields, field_name, field, field_value):

        if FieldUtils.value_is_empty(field_value):
            # User has removed the date after having
            # typed something. Everything is fine.
            return

        field_value = field_value.strip()

        if len(field_value) != 4:
            return (
                'Invalid year.'
            )

        try:
            _ = int(field_value)

        except Exception as e:
            return (
                'Invalid year, not understood: {exc}.'.format(exc=e)
            )

    def check_field_key(self, all_fields, field_name, field, field_value):

        field_value = field_value.strip()

        if KEY_RE.match(field_value) is None:
            return (
                'Key must start with a letter, contain only letters and numbers; special characters allowed: “-”, “:” and “_”.'
            )

        has_key = controllers.files.has_bib_key(field_value)

        if has_key:
            return (
                'Key already taken in <span '
                'face="monospace">{filename}</span>. '
                'Please choose another one.').format(
                    filename=os.path.basename(has_key)
            )

    def check_field_date(self, all_fields, field_name, field, field_value):

        if FieldUtils.value_is_empty(field_value):
            # User has removed the date after having
            # typed something. Everything is fine.
            return

        error_message = (
            'Invalid ISO date. '
            'Please type a date in the format YYYY-MM-DD.'
        )

        if len(field_value) < 10:
            return error_message

        try:
            _ = datetime.date.fromisoformat(field_value)

        except Exception as e:
            return '{error_message}\nExact error is: {exception}'.format(
                error_message=error_message, exception=e)

    check_field_urldate = check_field_date

    def check_field_url(self, all_fields, field_name, field, field_value):

        if FieldUtils.value_is_empty(field_value):
            # The URL was made empty after beiing set. Empty the date.
            FieldUtils.field_make_empty(all_fields['urldate'])
            return

        FieldUtils.field_set_date_today(all_fields['urldate'])

    # ————————————————————————————————————————————————————————————— Fix methods

    def fix_field_key(self, all_fields, field_name, field, field_value, entry, files):
        ''' Create a valid key. '''

        assert entry
        assert files

        new_key = generate_new_key(entry)
        counter = 1

        while files.has_bib_key(new_key):

            new_key = generate_new_key(entry, counter)
            counter += 1

        return new_key

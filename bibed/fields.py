
import logging
import datetime

from bibed.gtk import Gtk


LOGGER = logging.getLogger(__name__)


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

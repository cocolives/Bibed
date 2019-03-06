
import logging
import datetime
import dateutil.parser
import dateutil.tz

from datetime import timedelta

LOGGER = logging.getLogger(__name__)


def seconds_to_string(elapsed):

    # See https://stackoverflow.com/a/12344609/654755

    return str(timedelta(seconds=elapsed))


def datetime_extended_parser(aDateString):
    """ Custom date handler.

    See issue https://code.google.com/p/feedparser/issues/detail?id=404
    """

    try:
        return dateutil.parser.parse(aDateString).utctimetuple()

    except Exception:
        pass

    try:
        return dateutil.parser.parse(aDateString, ignoretz=True).utctimetuple()

    except Exception:
        pass

    default_datetime = datetime.datetime.now()

    try:
        return dateutil.parser.parse(aDateString,
                                     default=default_datetime).utctimetuple()

    except Exception:
        LOGGER.exception('Could not parse date string “%s” with '
                         'custom dateutil parser.', aDateString)
        # If dateutil fails and raises an exception, this produces
        # http://dev.1flow.net/1flow/1flow/group/30087/
        # and the whole chain crashes, whereas
        # https://pythonhosted.org/feedparser/date-parsing.html#registering-a-third-party-date-handler  # NOQA
        # states any exception is silently ignored.
        # Obviously it's not the case.
        return None

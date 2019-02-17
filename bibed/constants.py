import os
import bibtexparser

from bibed.user import (
    # import other CONSTANTS from sub-levels for higher levels.
    BIBED_LOG_DIR,
    BIBED_LOG_FILE,
)

from bibed.foundations import (
    Anything,
    BIBED_DATA_DIR,
    BIBED_ICONS_DIR,
)

from bibed.locale import C_

APP_ID = 'es.cocoliv.bibed'
APP_NAME = 'Bibed'
APP_VERSION = '0.9.11-develop'
BIBED_BACKGROUNDS_DIR = os.path.join(BIBED_DATA_DIR, 'backgrounds')

BIBED_SYSTEM_TRASH_NAME = 'trash.bib'
BIBED_SYSTEM_QUEUE_NAME = 'queue.bib'
BIBED_SYSTEM_IMPORTED_NAME = 'imported.bib'

BIBED_ASSISTANCE_FR = 'https://t.me/joinchat/AUg6sBK4qUXx2ApA0Zf-Iw'
BIBED_ASSISTANCE_EN = 'https://t.me/joinchat/AUg6sBUSeKHA3wubIyCwAg'

BIBTEXPARSER_VERSION = bibtexparser.__version__

MINIMUM_BIB_KEY_LENGTH = 8


BibAttrs = Anything((
    ('DBID', int, ),  # database ID (in file store)
    ('FILETYPE', int, ),  # file type
    ('COLOR', str, ),  # foreground color
    ('TOOLTIP', str, ),  # Row tooltip (for treeview)
    ('TYPE', str, ),  # BIB entry type (article, book…)
    ('KEY', str, ),  # BIB sort key
    ('FILE', str, ),  # file (PDF)
    ('URL', str, ),  # URL
    ('DOI', str, ),  # DOI
    ('AUTHOR', str, ),  # author
    ('TITLE', str, ),  # title
    ('SUBTITLE', str, ),  # subtitle
    ('JOURNAL', str, ),  # journal (or booktitle, howpublished… see entry.py)
    ('YEAR', int, ),  # year
    ('DATE', str, ),  # date
    ('QUALITY', str, ),  # quality
    ('READ', str, ),  # read status
    ('COMMENT', str, ),  # comment (text field)
    ('KEYWORDS', str, ),  # keywords (for search/filter only)
))


FileTypes = Anything()
FileTypes.SPECIAL   = 0xff00000
FileTypes.ALL       = 0x0100000
FileTypes.SEPARATOR = 0x8000000
FileTypes.SYSTEM    = 0x00ff000
FileTypes.TRASH     = 0x0001000
FileTypes.QUEUE     = 0x0002000
FileTypes.IMPORTED  = 0x0004000
FileTypes.TRANSIENT = 0x0080000
FileTypes.USER      = 0x0000fff
FileTypes.NOTFOUND  = 0x0000800


FILETYPES_COLORS = {
    FileTypes.SPECIAL   : '#000000',
    FileTypes.ALL       : '#000000',
    FileTypes.SEPARATOR : '#000000',
    FileTypes.SYSTEM    : '#000000',
    FileTypes.TRASH     : '#999',
    FileTypes.QUEUE     : '#6c6',
    FileTypes.TRANSIENT : '#afa',
    FileTypes.USER      : '#000000',
}

SEARCH_SPECIALS = (
    (C_('search field', 'p'),
     BibAttrs.TYPE,
     C_('search field', 'type'), ),
    (C_('search field', 'k'),
     BibAttrs.KEY,
     C_('search field', 'key'), ),
    (C_('search field', 'a'),
     BibAttrs.AUTHOR,
     C_('search field', 'author'), ),
    (C_('search field', 't'),
     BibAttrs.TITLE,
     C_('search field', 'title'), ),
    (C_('search field', 'j'),
     BibAttrs.JOURNAL,
     C_('search field', 'journal'), ),
    (C_('search field', 'y'),
     BibAttrs.YEAR,
     C_('search field', 'year'), ),
    (C_('search field', 'f'),
     BibAttrs.FILE,
     C_('search field', 'file'), ),
    (C_('search field', 'u'),
     BibAttrs.URL,
     C_('search field', 'URL'), ),
)


# See GUI constants later for icons.
JABREF_QUALITY_KEYWORDS = [
    'qualityAssured',
]

JABREF_READ_KEYWORDS = [
    'skimmed',
    'read',
]

# ———————————————————————————————————————————————————————————— GUI constants

APP_MENU_XML = '''
<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <menu id="app-menu">
    <section>
      <item>
        <attribute name="action">win.maximize</attribute>
        <attribute name="label" translatable="yes">Maximize</attribute>
      </item>
    </section>
    <section>
      <item>
        <attribute name="action">app.about</attribute>
        <attribute name="label" translatable="yes">_About</attribute>
      </item>
      <item>
        <attribute name="action">app.quit</attribute>
        <attribute name="label" translatable="yes">_Quit</attribute>
        <attribute name="accel">&lt;Primary&gt;q</attribute>
    </item>
    </section>
  </menu>
</interface>
'''

# Impossible to set background-opacity in GTK, and we don't have web hacks
# like div:after. Thus we need to prepare the background images with an
# already set transparency, like transparent PNGs or flattened JPEGs.
MAIN_TREEVIEW_CSS = '''
treeview.view:not(:selected),
treeview.view header button {
    background-color: transparent;
}

scrolledwindow#main {
    background-color: white;
    background-image: url("{background_filename}");
    background-size: {background_size};
    background-position: {background_position};
    background-repeat: no-repeat;
}
'''

BOXES_BORDER_WIDTH = 5

GRID_BORDER_WIDTH = 20
GRID_COLS_SPACING = 20
GRID_ROWS_SPACING = 20

SEARCH_WIDTH_MINIMAL = 20
SEARCH_WIDTH_MAXIMAL = 60

COMBO_CHARS_DIVIDER = 10

# TODO: remove this when search / combo are implemented as sidebar / searchbar
RESIZE_SIZE_MULTIPLIER = 0.20

# Expressed in percentiles of 1
COL_KEY_WIDTH     = 0.10
COL_TYPE_WIDTH    = 0.06
COL_AUTHOR_WIDTH  = 0.15
COL_JOURNAL_WIDTH = 0.15
COL_YEAR_WIDTH    = 0.04
# NOTE: col_title_width will be computed from remaining space.

# Expressed in pixels
COL_PIXBUF_WIDTH = 24
COL_SEPARATOR_WIDTH = 1
CELLRENDERER_PIXBUF_PADDING = 2

PANGO_BIG_FONT_SIZES = [
    14336,
    16384,
    18432,
    20480,
    22528,
    24576,
]

HELP_POPOVER_LABEL_MARGIN = 10

# Expressed in number of keywords (which can eventually be multi-words)
MAX_KEYWORDS_IN_TOOLTIPS = 20

# expressed in number of characters
ABSTRACT_MAX_LENGHT_IN_TOOLTIPS = 512
COMMENT_LENGHT_FOR_CR_IN_TOOLTIPS = 96


GENERIC_HELP_SYMBOL = (
    '<span color="grey"><sup><small>(?)</small></sup></span>'
)

READ_STATUS_PIXBUFS = {
    'read': None,
    '': 'bibed-property-unread',
    'skimmed': 'bibed-property-skimmed',
}

QUALITY_STATUS_PIXBUFS = {
    '': None,
    'qualityAssured': 'bibed-property-quality',
}

COMMENT_PIXBUFS = {
    False: None,
    True: 'bibed-property-comment',
}

URL_PIXBUFS = {
    False: None,
    True: 'bibed-property-url',
}

FILE_PIXBUFS = {
    False: None,
    True: 'bibed-property-pdf',
}

import os

APP_NAME = 'Bibed'
APP_VERSION = '1.0-develop'
APP_ID = 'es.cocoliv.bibed'
BIBED_DATA_DIR = os.path.join(os.path.realpath(
    os.path.abspath(os.path.dirname(__file__))), 'data')
BIBED_ICONS_DIR = os.path.join(BIBED_DATA_DIR, 'icons')


def icon(name):
    return os.path.join(BIBED_ICONS_DIR, name)


class Anything:
    pass


BibAttrs = Anything()

# Sync this with STORE_LIST_ARGS and entry:BibedEntry.to_list_store_row()
BibAttrs.GLOBAL_ID = 0
BibAttrs.FILENAME  = 1
BibAttrs.ID        = 2
BibAttrs.TOOLTIP   = 3
BibAttrs.TYPE      = 4
BibAttrs.KEY       = 5
BibAttrs.FILE      = 6
BibAttrs.URL       = 7
BibAttrs.DOI       = 8
BibAttrs.AUTHOR    = 9
BibAttrs.TITLE     = 10
BibAttrs.SUBTITLE  = 11
BibAttrs.JOURNAL   = 12
BibAttrs.YEAR      = 13
BibAttrs.DATE      = 14
BibAttrs.QUALITY   = 15
BibAttrs.READ      = 16
BibAttrs.COMMENT   = 17


STORE_LIST_ARGS = [
    int,  # global ID / counter across all files
    str,  # store origin (filename / ID)
    int,  # id / counter in current file
    str,  # Row tooltip (for treeview)
    str,  # BIB entry type
    str,  # BIB key
    str,  # file (PDF)
    str,  # URL
    str,  # DOI
    str,  # author
    str,  # title
    str,  # subtitle
    str,  # journal
    int,  # year
    str,  # date
    str,  # quality
    str,  # read status
    str,  # has comments
]

# See GUI constants later for icons.
JABREF_QUALITY_KEYWORDS = [
    'qualityAssured',
]

JABREF_READ_KEYWORDS = [
    'skimmed',
    'read',
]

PREFERENCES_FILENAME = 'bibed.yaml'
MEMORIES_FILENAME    = 'memories.yaml'
BIBED_APP_DIR_WIN32  = 'Bibed'
BIBED_APP_DIR_POSIX  = '.config/bibed'

# ———————————————————————————————————————————————————————————— GUI constants

APP_MENU_XML = """
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
"""

BOXES_BORDER_WIDTH = 5

GRID_BORDER_WIDTH = 20
GRID_COLS_SPACING = 20
GRID_ROWS_SPACING = 20

SEARCH_WIDTH_NORMAL   = 10
SEARCH_WIDTH_EXPANDED = 30

FILES_COMBO_DEFAULT_WIDTH = 25

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

GENERIC_HELP_SYMBOL = (
    '<span color="grey"><sup><small>(?)</small></sup></span>'
)

READ_STATUS_PIXBUFS = {
    'read': None,
    '': icon('16x16/book.png'),
    'skimmed': icon('16x16/book-open.png'),
}

QUALITY_STATUS_PIXBUFS = {
    '': None,
    'qualityAssured': icon('16x16/ranked.png'),
}

COMMENT_PIXBUFS = {
    False: None,
    True: icon('16x16/comment.png'),
}

URL_PIXBUFS = {
    False: None,
    True: icon('16x16/url.png'),
}

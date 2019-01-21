
APP_NAME = 'Bibed'
APP_VERSION = '1.0-develop'
APP_ID = 'es.cocoliv.bibed'


class Anything:
    pass


BibAttrs = Anything()

BibAttrs.GLOBAL_ID = 0
BibAttrs.FILENAME  = 1
BibAttrs.ID        = 2
BibAttrs.TYPE      = 3
BibAttrs.KEY       = 4
BibAttrs.FILE      = 5
BibAttrs.URL       = 6
BibAttrs.DOI       = 7
BibAttrs.AUTHOR    = 8
BibAttrs.TITLE     = 9
BibAttrs.JOURNAL   = 10
BibAttrs.YEAR      = 11
BibAttrs.DATE      = 12
BibAttrs.QUALITY   = 13
BibAttrs.READ      = 14

STORE_LIST_ARGS = [
    int,  # global ID / counter across all files
    str,  # store origin (filename / ID)
    int,  # id / counter in current file
    str,  # BIB entry type
    str,  # BIB key
    str,  # file (PDF)
    str,  # URL
    str,  # DOI
    str,  # author
    str,  # title
    str,  # journal
    int,  # year
    str,  # date
    str,  # quality
    str,  # read status
]

JABREF_QUALITY_KEYWORDS = [
    'qualityAssured',
]

JABREF_READ_KEYWORDS = [
    'read',
    'skimmed',
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

BOXES_BORDER_WIDTH    = 5

GRID_BORDER_WIDTH     = 20
GRID_COLS_SPACING     = 20
GRID_ROWS_SPACING     = 20

SEARCH_WIDTH_NORMAL   = 10
SEARCH_WIDTH_EXPANDED = 30

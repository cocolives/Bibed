
from bibed.foundations import Anything, Singleton
# from bibed.parallel import parallel_status
from bibed.store import BibedFileStore


class GlobalControllers(Anything, metaclass=Singleton):
    ''' Meta controller that will be filled at application load, for all
        subparts of application to get access to global controllers. '''

    def __init__(self):

        self.files = BibedFileStore()


# We expect to have:
#
#  - in main & background process:
#     - files (BibedFileStore)
#     - importer (BibedImporter)
#
#  - in main process:
#     - application (Gtk.Application)
#     - data (Gtk.ListStore)
#     - clipboard (Gtk.Clipboard)
#
# Any process accessing the controller should run files.load_system_files()
# after having loaded (or not) a Gtk data store.
controllers = GlobalControllers()

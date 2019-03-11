
from bibed.foundations import Anything, Singleton
from bibed.decorators import wait_for_queued_events
from bibed.store import BibedFileStore


class GlobalControllers(Anything, metaclass=Singleton):
    ''' Meta controller that will be filled at application load, for all
        subparts of application to get access to global controllers. '''

    def __init__(self):

        self.files = BibedFileStore()

    def stop(self, remember_close=True):

        self.files.close_all(save_before=False,
                             remember_close=remember_close)

        wait_for_queued_events()


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

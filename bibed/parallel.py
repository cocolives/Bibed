
from threading import Thread, Event

from bibed.gtk import Gtk


class BibedEventThread(Thread):

    def __init__(self, event, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.event = event

    def run(self):

        super().run()

        self.event.set()


# ————————————————————————————————————————————————————————————————————— Helpers
# https://wiki.gnome.org/Projects/PyGObject/Threading


def run_and_wait_on(func, *args, **kwargs):

    event = Event()
    # start thread on func with event

    thread = BibedEventThread(event, target=func, args=args, kwargs=kwargs)
    thread.start()

    while not event.is_set():
        while Gtk.events_pending():
            Gtk.main_iteration()

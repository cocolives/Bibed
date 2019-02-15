
import time
from bibed.gtk import Gtk, Gio
from bibed.gui.css import GtkCssAwareMixin


class SplashApp(Gtk.Application, GtkCssAwareMixin):

    def __init__(self, **kwargs):

        self.splash = kwargs.pop('splash')

        super().__init__()

        self.setup_resources_and_css()

        action = Gio.SimpleAction.new('quit', None)
        action.connect('activate', self.on_quit)
        self.add_action(action)

    def do_activate(self):

        print('ACTIVATE START')

        for i in range(500):
            while Gtk.events_pending():
                Gtk.main_iteration()
            time.sleep(0.1)

        print('ACTIVATE END')

    def on_quit(self):

        self.splash.close()
        self.quit()


if __name__ == "__main__":

    from bibed.gtk import Gtk
    from bibed.gui.splash import start_splash

    splash = start_splash()

    SplashApp(splash=splash).run()

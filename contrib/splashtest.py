
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

        # Need to call Gtk.main to draw all widgets
        while Gtk.events_pending():
            Gtk.main_iteration()

        for i in range(10):
            Gtk.main_iteration_do(True)

        # print('ACTIVATE')

        # time.sleep(1)

        print('ACTIVATE MAIN')

        # Need to call Gtk.main to draw all widgets
        while Gtk.events_pending():
            Gtk.main_iteration()

        print('ACTIVATE MAIN END → sleeping…')

        time.sleep(5)

        print('ACTIVATE END')

    def on_quit(self):

        self.splash.close()
        self.quit()


if __name__ == "__main__":

    from bibed.gtk import Gtk
    from bibed.gui.splash import start_splash

    splash = start_splash()

    SplashApp(splash=splash).run()

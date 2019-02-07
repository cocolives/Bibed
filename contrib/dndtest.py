
from bibed.gui.dndflowbox import dnd_scrolled_flowbox
from bibed.gui.splash import BibedSplashWindow
from bibed.gtk import Gtk


class DragDropWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="Drag and Drop Demo")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        hbox = Gtk.Box(spacing=12)
        vbox.pack_start(hbox, True, True, 0)

        (self.aframe, self.ascrolled, self.adnd_area) = dnd_scrolled_flowbox(
            name='main', title='Main', dialog=self)

        (self.bframe, self.bscrolled, self.bdnd_area) = dnd_scrolled_flowbox(
            name='other', title='Other', dialog=self)

        hbox.pack_start(self.aframe, True, True, 0)
        hbox.pack_start(self.bframe, True, True, 0)

        self.adnd_area.add_items(['ardoise', 'artichaud', 'aboiement'])
        self.bdnd_area.add_items(['bateau', 'bigorneau', 'bouteille'])

        self.set_size_request(500, 500)

    def update_dnd_preferences(self):

        print('A CHILDREN:', self.adnd_area.get_children_names())
        print('B CHILDREN:', self.bdnd_area.get_children_names())


if __name__ == '__main__':

    win = DragDropWindow()
    # win = BibedSplashWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

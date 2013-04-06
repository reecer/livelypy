import gtk
import sys;

class TestNotebook(gtk.Notebook):
    def __init__(self):
        gtk.Notebook.__init__(self)

    def add_new_tab(self, icon):
        image = gtk.Image()
        image.set_from_stock(icon, gtk.ICON_SIZE_DIALOG)
        image.show_all()        

        tab_image = gtk.Image()
        tab_image.set_from_stock(icon, gtk.ICON_SIZE_MENU)

        box = gtk.HBox()
        box.pack_start(tab_image, False, False)
        box.pack_start(gtk.Label(icon), True, True)
        # set tab size here
        box.set_size_request(50, 50)        
        box.show_all()

        self.set_current_page(self.append_page(image))
        self.set_tab_label(image, box)

if __name__ == '__main__':
    notebook = TestNotebook()
    notebook.add_new_tab(gtk.STOCK_ABOUT)
    notebook.add_new_tab(gtk.STOCK_ADD)
    notebook.add_new_tab(gtk.STOCK_APPLY)

    box = gtk.VBox()
    box.pack_start(notebook)
    gtk.main()
import gtk, gobject
from pieces import *
from utils import PyCompiler
import Queue

VERSION = '0.2'

class PyPad:
        def on_quit(self,e, f):
                ns = range(self.notebook.get_n_pages())
                ns.reverse()
                for n in ns:
                        page = self.notebook.get_nth_page(n)
                        page.close()
                gtk.main_quit()
        def __init__(self):
                # Compiler queue's
                self.inQue = Queue.Queue()
                self.outQue = Queue.Queue()
                # Instances
                self.window = gtk.Window()
                self.notebook = gtk.Notebook()
                self.statusbar = gtk.Statusbar()
                self.inspector = Inspector(self)
                self.completer = self.inspector.completer
                self.compiler = PyCompiler(self.inQue, self.outQue)
                self.compiler.start()

                # Random vars
                self.status = 'ERROR: None'
                self.status_id = self.statusbar.get_context_id("main") # for setting status
                self.fullscreen = False
                self.current_obj = None     # obj left of cursor
                gobject.timeout_add(600, self.compile_current)
                 # pack?
                vbox = gtk.VBox()
                vbox.pack_start(self.notebook)
                vbox.pack_start(self.statusbar, expand=False)
                # for completer
                hbox = gtk.HBox()
                hbox.pack_start(vbox)
                hbox.pack_end(self.inspector, False, False)
                self.window.add(hbox)
                # window settings
                self.window.set_title("PyPad " + VERSION)
                self.window.set_size_request(900,600)
                self.window.set_position(gtk.WIN_POS_CENTER)
                self.window.set_icon_from_file('icon.png')
                self.window.connect("delete-event", self.on_quit)
                self.window.connect('key-press-event', self.on_keypress)
                self.window.show_all()
                self.set_status('PyPad!')
        def on_keypress(self, window, event):
                if event.state & gtk.gdk.CONTROL_MASK:
                        if event.keyval in range(256):
                                key = chr(event.keyval).lower()
                                if   key == 'o': self.open_file()
                                elif key == 'n': self.new_file()
                                elif key == 'w': self.close_current()
                                elif key == 's': self.save_current()
                                elif key == 'e': self.get_current().eval_here()
                                else:
                                        print 'ctrl+',chr(event.keyval)
                elif event.state & gtk.gdk.MOD1_MASK:
                        if event.keyval == gtk.keysyms.Return:
                                self.inspector.completer.select_entry()
                        elif event.keyval == gtk.keysyms.Down:
                                self.inspector.completer.move_down()
                        elif event.keyval == gtk.keysyms.Up:
                                self.inspector.completer.move_up()
                        return True # Ignore textview event

        def set_status(self,status):
                msg = str(status)
                self.status = msg
                self.statusbar.push(self.status_id, msg)

        def new_file(self, fpath=None):
                """Create a new page."""
                page = Page(self)
                label_box = TabLabel(page)
                self.notebook.append_page(page, label_box)
                # set tab sizes

                if fpath:
                        page.open(fpath)
                        index = fpath.replace("\\","/").rfind("/") + 1
                        page.set_label(fpath[index:])
                else:
                        page.set_label('untitled')
                page.show_all()
                self.notebook.set_page(self.notebook.page_num(page))
                page.edit.grab_focus()
        def open_file(self):
                files = choose_file()
                for f in files:
                        self.new_file(f)
        def compile_current(self):
                """Compiles the current page"""
                page = self.get_current()
                if page and page.edit.changed:
                        page.edit.changed = False
                        page.compile()
                return True # to repeat
        def get_current(self):
                """Returns the Page object of the focused tab"""
                return self.notebook.get_nth_page(self.notebook.get_current_page())
        def close_current(self):
                """Close current notebook page"""
                p = self.get_current()
                if p: p.close()
        def save_current(self):
                """Save current notebook page"""
                p =self.get_current()
                if p: p.save()


if __name__ == '__main__':
        p =PyPad()
        gtk.main()  
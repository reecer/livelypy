import gtk,gtksourceview2
import inspect
####################################
# The main source code editor
####################################
class PyEditor(gtksourceview2.View):
    """ Main editor """
    def __init__(self, page):
        super(PyEditor, self).__init__()
        self.page = page
        # Random vars
        self.changed = False
        errpng = gtk.gdk.pixbuf_new_from_file('error.png')

        #set buffer with python syntax
        self.buf = gtksourceview2.Buffer()
        self.buf.connect("changed", self.on_change)
        self.connect("move-cursor", self.curs_moved)
        langs = gtksourceview2.LanguageManager()
        py = langs.get_language('python')
        self.buf.set_language(py)   

        self.set_buffer(self.buf)
        self.set_mark_category_pixbuf('error', errpng)
        self.set_show_line_marks(True)
        self.set_auto_indent(True)
        self.set_show_line_numbers(True)
        self.set_highlight_current_line(True)
        self.set_has_tooltip(True)
    def open(self, fpath):
        with open(fpath, 'r') as f:
            self.buf.set_text(f.read())
    def save(self): # these two should ideally be in Page
        if self.page.full_path:
            with open(self.page.full_path, 'w') as f:
                f.write(self.text())
                title = self.page.get_label()
                if title.endswith('*'):
                    self.page.set_label(title[:-1])
        else:
            choice = choose_file(False)
            if choice:
                self.page.full_path = choice
                self.save()
    def curs_moved(self, view=None, step=None, count=None, selected=None):
        self.page.pypad.completer.update(self.page) # redundant method; self.page is alrdy parent
        if selected:
            self.page.eval_here()
    def on_change(self,bufr):
        self.changed = True
        title = self.page.get_label()
        if not title.endswith('*'):
            self.page.set_label(title+ "*")
        self.curs_moved()
        
    def get_current_word(self):
        """Retrieves the word behind the cursor. Also returns offset.
           Keeps moving backward until no more words are seperated by a '.'"""
        itr_right = self.buf.get_iter_at_mark(self.buf.get_insert()) #cursor pos
        itr_left = itr_right.copy()

        while itr_left.get_char() not in (' ', '(', '\n'):
            if not itr_left.backward_char():
                break
        if not itr_left.is_start():
            itr_left.forward_char()
        word = self.buf.get_slice(itr_left, itr_right)
        return word, itr_right.get_offset()

    def set_error(self, line):
        """Show red dot in the margin"""
        # remove errors
        self.buf.remove_source_marks(self.buf.get_start_iter(), self.buf.get_end_iter())
        if line: # set error
                self.buf.create_source_mark(None, 'error', self.buf.get_iter_at_line(line-1))
    def text(self):
        buf = self.get_buffer()
        return buf.get_text(buf.get_start_iter(), buf.get_end_iter())

    def cursor_coords(self):
        itr = self.buf.get_iter_at_mark(self.buf.get_insert())
        iter_location = self.get_iter_location(itr)
        win_location = self.buffer_to_window_coords(gtk.TEXT_WINDOW_WIDGET, iter_location.x, iter_location.y)

        win = self.get_window(gtk.TEXT_WINDOW_WIDGET)
        view_pos = self.get_toplevel().get_position()


        xx = win_location[0] + view_pos[0]
        yy = win_location[1]+ view_pos[1] + iter_location.height;     
            
        top_x, top_y = win.get_position()
        return (xx+top_x, yy+top_y) 
        



####################################
# A page in the notebook. Connects thigns
####################################
class Page(gtk.ScrolledWindow):
    def __init__(self, pypad):
        super(Page, self).__init__()
        self.pypad = pypad
        self.book = pypad.notebook
        self.edit = PyEditor(self)
        self.full_path = None
        self.frameStack = None
        self.globals = {}

        self.add(self.edit)
    def open(self, fpath):
        self.full_path = fpath
        self.edit.open(fpath)
    def close(self, evt=None):
        if self.full_path: # save and remove
            self.save()
            self.book.remove_page(self.book.page_num(self))
        elif self.edit.text() == '':
            self.book.remove_page(self.book.page_num(self))            
        else:
            should_save = save_b4_quit()
            if should_save == gtk.RESPONSE_YES:
                self.full_path = choose_file(False)
                self.close()
            elif should_save == gtk.RESPONSE_NO:# just remove
                self.book.remove_page(self.book.page_num(self))
            # else dont close

    def save(self):
        self.edit.save()
    def set_label(self, txt):
        label = self.book.get_tab_label(self)
        label.set_text(txt)
    def get_label(self):
        label =  self.book.get_tab_label(self)
        return label.get_text()


    def eval_here(self):
        """Evaluate current word or selected word"""
        buf = self.edit.get_buffer() 
        word = ''
        if buf.get_has_selection():
            a, b = buf.get_selection_bounds()
            word = buf.get_slice(a,b)
        else:
            word = self.edit.get_current_word()[0]
        self.pypad.set_status(word + ' = ' + str(self.evaluate(word)))
    def evaluate(self, word):
        """Evaluate selected text OR current word?"""
        loces = self.current_locals()
        globes = self.current_locals(globalsInstead=True)

        if word in loces:           # in locals?
            return eval(word, loces)
        elif word in self.globals:  # in globals?
            return eval(word, self.globals)
        elif word in globes:
            return eval(word, globes)
        else:
            return None
    #   
    #       COMPILER STUFF
    #
    def compile(self):
        """Compile src and distribute output"""
        src = self.edit.text()
        self.pypad.inQue.put(src)
        out = self.pypad.outQue.get()         
        # compiler feedback
        self.compile_info(out)
    
    def compile_info(self,out):
        """Given compiler output, set globals, framestack, and error"""
        error = out['error']
        msg = error[0] # traceback
        lno = error[1]
        self.edit.set_error(lno)
        if msg: # error
            self.pypad.set_status('ERROR: ' + error[2])
        else: # no errors
            self.globals = out['globals']
            self.frameStack = out['frames']
            if self.pypad.status.startswith("ERROR: "):
                self.pypad.set_status("No errors")
                            
    def current_locals(self, globalsInstead=False):
        """Given a lineno, use the frameStack to find locals at line lineno"""
        if not self.frameStack: return {}
        frames = self.frameStack
        localz = frames[0]

        buf = self.edit.get_buffer()
        pos = buf.get_iter_at_mark(buf.get_insert())
        lineno = pos.get_line()+1 # current line number
        for f in frames:
                first = f.f_code.co_firstlineno 
                last = f.f_lineno
                if lineno in range(first, last+1):
                    localz = f

        if globalsInstead:
            return localz.f_globals 
        return localz.f_locals





class Inspector(gtk.VBox):
    def __init__(self, pypad):
        super(Inspector, self).__init__()
        self.pypad = pypad
        self.completer = CodeCompleter(self)
        self.evaluator = gtk.TextView() # for now

        self.word_label = gtk.Label()
        self.word_label.set_use_markup(True)
        self.set_word("test.", "word")

        scroll = gtk.ScrolledWindow()
        scroll.add(self.evaluator)

        top = gtk.VBox()
        top.pack_start(self.word_label, False, False)
        top.pack_end(self.completer)

        self.pack_start(top)
        self.pack_end(scroll)
    def set_word(self, word, prefix):
        first = "<span foreground='blue'>%s</span>" % word
        last = "<span foreground='red'>%s</span>" % prefix
        self.word_label.set_label(first + last)

    def set_doc(self, obj, isdoc=True):
        txt=''
        if isdoc:
            txt = '%s\n%s' % (str(obj), inspect.getdoc(obj))
        else:
            txt = str(obj)
        self.evaluator.get_buffer().set_text(txt)




####################################
# The code completer
####################################        
class CodeCompleter(gtk.Frame):
    def __init__(self, insptr):
        super(CodeCompleter, self).__init__()

        self.set_size_request(350,20)
        self.pypad = insptr.pypad
        self.inspector = insptr
        self.page = None
        self.editor = None
        self.buffer = None
        
        # globals
        self.pos = None # offset of cursor
        self.word = self.prefix = ''
        self.store = gtk.ListStore(str)
        self.view  = gtk.TreeView(self.store)
        self.view.set_headers_visible(False)
        self.view.connect("cursor-changed", self.show_info)
        # tree crap
        cell = gtk.CellRendererText() 
        column = gtk.TreeViewColumn("Options")        
        column.pack_start(cell, False)
        column.add_attribute(cell, "text", 0)
        # in a scrollwindow
        self.view.append_column(column)
        scroll = gtk.ScrolledWindow()
        scroll.add(self.view)

        self.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.add(scroll)

    def move_down(self):
        path, column = self.view.get_cursor()
        if path:
            self.view.set_cursor((path[0] + 1,)) # Down

    def move_up(self):
        path, column = self.view.get_cursor()
        if path:
            self.view.set_cursor((path[0] - 1,)) # Up

    def select_entry(self):
        src = self.editor.text()
        a = self.pos
        b = a - len(self.prefix)
        src = src[:b] + self.get_entry()
        self.buffer.set_text(src)

    def get_entry(self):
        selection = self.view.get_selection()
        store,itr = selection.get_selected()
        if itr:
            entry = store.get_value(itr, 0)
            return entry
        else: return ''

    def show_info(self, tree=None):
        """Shows info for current completer suggestion"""
        doc = self.page.evaluate(self.word + self.get_entry())
        print doc
        print self.word + self.get_entry()

        self.inspector.set_doc(doc)

    def set_page(self, page):
        self.page = page
        self.editor = page.edit
        self.buffer = page.edit.get_buffer()

    def update(self, page):
        """Updates the code completion by displaying
           words that start with var prefix. Returns True
           if find a match. False otherwise."""
        self.set_page(page)
        word, self.pos = self.editor.get_current_word()
        
        # determin prefix
        prefix = ''
        if len(word.split('.')) > 1:
            prefix = word.split('.')[-1]
            if len(prefix):
                word = word[:-len(prefix)]

        self.inspector.set_word(word, prefix)
        # new method - create a new list every time
        # remove based on prefix
        suggs = [] 
        if word.endswith('.'):
            obj = self.page.evaluate(word[:-1])
            if obj:
                dirs = dir(obj)
                prefix = prefix.lower()
                for s in dirs: # starting with first
                    if s.lower().startswith(prefix):
                        suggs.append(s)
                for s in dirs: # in word second
                    if prefix in s.lower() and s not in suggs:
                        suggs.append(s)
        elif self.page.globals:
            for g in self.page.globals:
                suggs.append(g)
        self.setList(suggs) 
        self.word = word
        self.prefix = prefix
        self.show_info()
    def setList(self,l):
        self.store.clear()
        for x in l: self.store.append([str(x)])
        self.view.set_cursor((0,))
        self.show_info()
        











###########################################
# Box for page's tab. Contains a label/close button
###########################################
class TabLabel(gtk.HBox):
    def __init__(self, page):
        super(TabLabel, self).__init__()
        b_img = gtk.Image()
        b_img.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
        # create label/button
        self.label = gtk.Label()
        close_button = gtk.Button()
        close_button.set_image(b_img)
        close_button.connect("clicked", page.close)
        
        self.pack_start(self.label)
        self.pack_start(close_button, False, False)
        self.show_all()
    def set_text(self,txt):
        self.label.set_label(txt)
    def get_text(self):
        return self.label.get_text()












###########################################
# DIALOG HELPERS
###########################################    
def choose_file(multi=True):
    """Chooses where to open (True) or save (False)
        a file. Returns None on Cancel"""
    title = "Open a file"
    action = gtk.FILE_CHOOSER_ACTION_OPEN
    if not multi: # False if saving
        title = "Save file"
        action = gtk.FILE_CHOOSER_ACTION_SAVE
    chooser = gtk.FileChooserDialog(title=title,action=action, 
            buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
    chooser.set_select_multiple(multi)
    chooser.set_default_response(gtk.RESPONSE_OK)
    resp = chooser.run()
    fs = []
    if resp == gtk.RESPONSE_OK:
        if multi:
            for f in chooser.get_filenames():
                fs.append(f)
        else: 
            fs = chooser.get_filename()
    else: fs = None
    chooser.destroy()
    return fs

def save_b4_quit():
    """Message dialog. Returns dialog response"""
    win = gtk.MessageDialog(buttons=(gtk.BUTTONS_YES_NO))
    win.set_markup("Would you like to save this file?")
    resp = win.run()
    win.destroy()
    return resp
import threading, sys
import inspect
from cStringIO import StringIO
###########################################
# Compiler thread. Collects frames/errors #
###########################################
class PyCompiler(threading.Thread):
        """Compile python src given on q1 and outputs on q2"""
        def __init__(self, q1, q2):
                threading.Thread.__init__(self)
                self.quit = threading.Event()
                self.inqueue = q1
                self.outqueue = q2
                self.stack = []

        def run(self):
                while not self.quit.isSet():
                        if not self.inqueue.empty():
                                self.stack = []
                                src = self.inqueue.get()
                                ers_frms = self.exec_python(src)
                                self.outqueue.put(ers_frms)

        def exec_python(self, src):
                """Where the magic happends"""
                # STDOUT stuff
                sys.stdout = out = StringIO()
                std_out = 'stdout'
                error_msg = None
                error_line = None
                error_status = None
                globes = {}
                sys.settrace(self.twace)
                ##############################################################################          
                #                                                       EXECUTE IT           #
                try: 
                    piled = compile(src, '<string>', 'exec')
                    exec(piled, globes)
                #  ERROR HANDLING  #
                except Exception as e:
                    sys.settrace(None)
                    error_msg = ''
                    if hasattr(e, 'lineno'): 
                            error_line = e.lineno
                    else:
                            t_stack = inspect.trace()
                            error_msg += "\n TRACEBACK\n" + "-" * 24
                            for i in t_stack[1:]:
                                    error_msg += '\nLine %d in %s:\n\tin %s:\n' % (i[2], i[1], i[3])
                                    if t_stack.index(i) == 1: error_line = i[2]
                                    if i[4]: error_msg += '\t>> %s' % i[4][0].strip()       
                    # append sys_exc info
                    sysinf = sys.exc_info() 
                    error_status = str(sysinf[1])
                    error_msg += '\n' + error_status
                #                                                                            #
                ##############################################################################          
                sys.settrace(None)
                std_out = out.getvalue()[:]
                out.close()
                sys.stdout = sys.__stdout__#preserve
                outp = {
                        "error" : [error_msg, error_line, error_status],
                        "stdout" : std_out,
                        "frames" : self.stack,
                        "globals": globes
                }
                return outp
        
        def twace(self, frame, event, args):
                """Sys trace while compiling"""
                if event == 'call' and frame.f_code.co_filename == '<string>':
                        self.stack.append(frame)
                return self.twace
        # clean up
        def join(self, timeout=None):
                self.quit.set()
                super(PyCompiler, self).join(timeout)

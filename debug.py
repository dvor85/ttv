﻿# -*- coding: utf-8 -*-
import sys,os

# append pydev remote debugger
# Make pydev debugger works for auto reload.
try:        
    sys.path.append(os.path.expanduser('~/liclipse/plugins/org.python.pydev_5.1.2.201606231040/pysrc'))
    sys.path.append('d:/python/eclipse/plugins/org.python.pydev_4.4.0.201510052309/pysrc')
    
    import pydevd  # with the addon script.module.pydevd, only use `import pydevd`
          
    pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True)
except:
    t, v, tb = sys.exc_info()        
    print "{0}:{1}".format(t, v)
    print "For remote debug in eclipse you must append org.python.pydev.pysrc to sys.path."
    print "Or install script.module.pydevd addon."
    print "Append it to your PYTHONPATH for code completion."
    print "CONTINUE WITHOUT DEBUGING"
    import traceback
    traceback.print_tb(tb)
    del tb
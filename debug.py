# -*- coding: utf-8 -*-
import sys
import os

# append pydev remote debugger
# Make pydev debugger works for auto reload.
try:
    sys.path.append(os.path.expanduser('~/eclipse/plugins/org.python.pydev_5.5.0.201701191708/pysrc'))
    sys.path.append('d:/python/eclipse/plugins/org.python.pydev_5.5.0.201701191708/pysrc')
    sys.path.append('c:/test/org.python.pydev_5.4.0.201611281236.zip')

    import pydevd
    # for remote debug edit pydevd_file_utils.py on client
    pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True)
except:
    t, v, tb = sys.exc_info()
    print "{0}:{1}".format(t, v)
    print "For remote debug in eclipse you must append org.python.pydev.pysrc to sys.path."
    print "Append it to your PYTHONPATH for code completion."
    print "CONTINUE WITHOUT DEBUGING"
    import traceback
    traceback.print_tb(tb)
    del tb

# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals
import sys
import os
import platform
# append pydev remote debugger
# Make pydev debugger works for auto reload.
try:
    #     sys.path.insert(0, os.path.expanduser('~/org.python.pydev_4.5.5.201603221110/pysrc'))
    #
    if platform.system() == 'Linux':
        print "Append pydevd for Linux"
        sys.path.insert(0, os.path.expanduser('~/eclipse/plugins/org.python.pydev.core_7.3.0.201908161924/pysrc'))
    elif platform.system() == 'Windows':
        print "Append pydevd for Windows"
        sys.path.insert(0, 'd:\\python\\eclipse\\plugins\\org.python.pydev.core_7.3.0.201908161924\\pysrc')
    # print sys.path
#
    #     sys.path.append('d:/python/eclipse/plugins/org.python.pydev_5.5.0.201701191708/pysrc')
    #     sys.path.append('i:/python/eclipse/plugins/org.python.pydev_5.5.0.201701191708/pysrc')

    #     import web_pdb
    #     web_pdb.set_trace()
    # for remote debug edit pydevd_file_utils.py on client
    import pydevd
    pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True, suspend=False)
except Exception:
    t, v, tb = sys.exc_info()
    print "{0}:{1}".format(t, v)
    print "For remote debug in eclipse you must append org.python.pydev.pysrc to sys.path."
    print "Append it to your PYTHONPATH for code completion."
    print "CONTINUE WITHOUT DEBUGING"
    import traceback
    traceback.print_tb(tb)
    del tb

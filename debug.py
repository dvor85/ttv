# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


import platform
import sys
import os


# remote debugging with eclipse pydevd
# append pydev remote debugger
# Make pydev debugger works for auto reload.
if platform.system() == 'Linux':
    print("Append pydevd for Linux")
    sys.path.insert(0, os.path.expanduser('~/eclipse/plugins/org.python.pydev.core_10.0.2.202212101256/pysrc'))
elif platform.system() == 'Windows':
    print("Append pydevd for Windows")
    sys.path.insert(0, 'd:\\python\\eclipse\\plugins\\org.python.pydev.core_8.3.0.202104101217\\pysrc')

import pydevd  # @UnresolvedImport @IgnorePep8
pydevd.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True, suspend=False)


"""
# remote debugging with pycharm pydevd
if platform.system() == 'Linux':
    print("Append pydevd for Linux")
elif platform.system() == 'Windows':
    print("Append pydevd for Windows")
    sys.path.insert(0, 'c:\\Program Files\\JetBrains\\PyCharm 2019.2\\debug-eggs\\pydevd-pycharm.egg')

import pydevd_pycharm
pydevd_pycharm.settrace('127.0.0.1', port=12345, stdoutToServer=True, stderrToServer=True, suspend=False)
"""

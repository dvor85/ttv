# Copyright (c) 2013 Torrent-TV.RU
# Writer (c) 2011, Welicobratov K.A., E-mail: 07pov23@gmail.com

import os, sys

REMOTE_DBG = True 

# append pydev remote debugger
if REMOTE_DBG:
    # Make pydev debugger works for auto reload.
    # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
    try:
        import pysrc.pydevd as pydevd  # with the addon script.module.pydevd, only use `import pydevd`
        # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse console
        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True)
    except:
        t, v, tb = sys.exc_info()        
        sys.stderr.write("Error: {0}:{1} | You must add org.python.pydev.debug.pysrc to your PYTHONPATH.".format(t, v))
        import traceback
        traceback.print_tb(tb)
        del tb
    

import xbmc
import xbmcaddon
import cPickle
import defines
import os

import mainform 
from okdialog import OkDialog

def checkPort(params):
    if not defines.checkPort(params):
        
        #dialog = OkDialog("okdialog.xml", defines.SKIN_PATH, defines.ADDON.getSetting('skin'))
        #dialog.setText("Порт %s закрыт. Для стабильной работы сервиса и трансляций, настоятельно рекомендуется его открыть." % defines.ADDON.getSetting('outport'))
        #dialog.doModal()
        pass

if __name__ == '__main__':
    if not defines.ADDON.getSetting('skin'):
        defines.ADDON.setSetting('skin', 'st.anger')
    if defines.ADDON.getSetting("skin") == "default":
        defines.ADDON.setSetting("skin", "st.anger")
    if not defines.ADDON.getSetting("login"):
        defines.ADDON.setSetting("login", "anonymous")
        defines.ADDON.setSetting("password", "anonymous")

    thr = defines.MyThread(checkPort, defines.ADDON.getSetting("outport"))
    thr.start()

    print defines.ADDON_PATH
    print defines.SKIN_PATH
    w = mainform.WMainForm("mainform.xml", defines.SKIN_PATH, defines.ADDON.getSetting('skin'))
    w.doModal()
    defines.showMessage('Close plugin')
    del w
    
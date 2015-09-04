# -*- coding: utf-8 -*-
# Copyright (c) 2013 Torrent-TV.RU
# Writer (c) 2011, Welicobratov K.A., E-mail: 07pov23@gmail.com
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import sys
import defines
import xbmc


if defines.DEBUG == xbmc.LOGDEBUG:
    # append pydev remote debugger
    # Make pydev debugger works for auto reload.
    # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
    #Add "sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), '..')))" to 
    #special://xbmc/system/python/Lib/pysrc/_pydev_imps/_pydev_pluginbase.py
    try:        
        #try:
        import pysrc.pydevd as pydevd  # with the addon script.module.pydevd, only use `import pydevd`            
        #except:
        #import os
        #sys.path.append(os.path.join(xbmc.translatePath("special://home/addons"), 'script.module.pydevd/lib'))
        #import pydev
        # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse console
        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True)
    except:
        t, v, tb = sys.exc_info()        
        defines.LogToXBMC("{0}:{1} | For remote debug in eclipse you must add org.python.pydev.debug.pysrc to your PYTHONPATH or install script.module.pydevd addon.".format(t, v), xbmc.LOGERROR)
        defines.LogToXBMC("CONTINUE WITHOUT DEBUGING", xbmc.LOGERROR)
        import traceback
        traceback.print_tb(tb)
        del tb
    



def checkPort(params):
    if not defines.checkPort(params):
        mess = "Порт %s закрыт. Для стабильной работы сервиса и трансляций, настоятельно рекомендуется его открыть." % defines.ADDON.getSetting('outport')
        defines.showMessage(mess)
        defines.LogToXBMC(mess)
        
def main():
    import mainform 
    if not defines.ADDON.getSetting('skin'):
        defines.ADDON.setSetting('skin', 'st.anger')
    if defines.ADDON.getSetting("skin") == "default":
        defines.ADDON.setSetting("skin", "st.anger")
    if not defines.ADDON.getSetting("login"):
        defines.ADDON.setSetting("login", "anonymous")
        defines.ADDON.setSetting("password", "anonymous")

    
    #defines.MyThread(checkPort, defines.ADDON.getSetting("outport")).start()
    defines.MyThread(defines.Autostart, defines.AUTOSTART).start()
    
    w = mainform.WMainForm("mainform.xml", defines.SKIN_PATH, defines.ADDON.getSetting('skin'))
    w.doModal()
    defines.showMessage('Close plugin')
    del w

if __name__ == '__main__':
    main()
    
    
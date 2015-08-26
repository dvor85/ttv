# -*- coding: utf-8 -*-
# Copyright (c) 2010-2011 Torrent-TV.RU
# Writer (c) 2011, Welicobratov K.A., E-mail: 07pov23@gmail.com
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

# imports
import os
import xbmc
from mainform import WMainForm
# from player import MyPlayer
# from TSCore import TSengine as tsengine

# defines
import defines

LogToXBMC = defines.Logger('GUI')

ACE_PORT = 62062
CANCEL_DIALOG = (9, 10, 11, 92, 216, 247, 257, 275, 61467, 61448,)
BTN_CHANNELS_ID = 102
BTN_TRANSLATIONS_ID = 103
BTN_CLOSE = 101

try:
    if defines.PTR_FILE:  
        with open(defines.PTR_FILE, 'r') as gf:
            ACE_PORT = int(gf.read())
except: PTR_FILE = None
if not PTR_FILE:
    try:
        fpath = os.path.expanduser("~")
        pfile = os.path.join(fpath, 'AppData\Roaming\TorrentStream\engine' , 'acestream.port')
        with open(pfile, 'r') as gf:
            ACE_PORT = int(gf.read())
        defines.ADDON.setSetting('port_path', pfile)
        LogToXBMC(ACE_PORT, xbmc.LOGDEBUG)
    except: ACE_PORT = 62062

# functions
def showMessage(message='', heading='Torrent-TV.RU', times=3000, pics=defines.ADDON_ICON):
    try: xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s, "%s")' % (heading.encode('utf-8'), message.encode('utf-8'), times, pics.encode('utf-8')))
    except Exception, e:
        try: xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s, "%s")' % (heading, message, times, pics))
        except Exception, e:
            LogToXBMC('showMessage: exec failed [%s]' % e, xbmc.LOGERROR)


def main():
    ui = WMainForm("DialogDownloadProgress.xml", defines.ADDON_PATH, 'default')
    ui.show()
    # thr = _DBThread(start, None)
    # thr.start()
    # xbmc.executebuiltin( "XBMC.PreviousMenu")
    while not ui.IsCanceled():
        # del ui
        # label = ui.getControl(104)
        # label.setVisible(False)
        
        xbmc.sleep(975)

# -*- coding: utf-8 -*-
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import xbmcaddon
import xbmc
import sys
import urllib2
import threading
import os
from BeautifulSoup import BeautifulSoup

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_ICON = ADDON.getAddonInfo('icon')
PTR_FILE = ADDON.getSetting('port_path')
DATA_PATH = xbmc.translatePath(os.path.join("special://profile/addon_data", ADDON_ID))
TTV_VERSION = '1.5.3'
AUTOSTART = ADDON.getSetting('startlast') == 'true'

try:
    DEBUG = int(ADDON.getSetting('debug'))
except:
    DEBUG = xbmc.LOGNOTICE
    ADDON.setSetting('debug', str(DEBUG))
    
if sys.platform.startswith('win'):
    ADDON_PATH = ADDON_PATH.decode('utf-8')
    DATA_PATH = DATA_PATH.decode('utf-8')

SKIN_PATH = ADDON_PATH
skin = ADDON.getSetting('skin')
if (skin != None) and (skin != "") and (skin != 'st.anger'):
    SKIN_PATH = DATA_PATH

closeRequested = threading.Event()

class Logger():
    
    def __init__(self, tag, minlevel=DEBUG):
        self.tag = tag
        self.minlevel = minlevel
        
    def __call__(self, msg, level=xbmc.LOGNOTICE):
        self.log(msg, level)
        
    def log(self, msg, level):
        if level >= self.minlevel:
            xbmc.log("[{id}::{tag}] {msg}".format(**{'id':ADDON_ID, 'tag':self.tag, 'msg': msg}), level)
            
LogToXBMC = Logger('DEFINES')

    
def Autostart(state):
    autoexec = os.path.join(xbmc.translatePath("special://masterprofile"), 'autoexec.py')

    if os.path.isfile(autoexec): 
        mode = 'r+' 
    elif state: 
        mode = 'w+'     
    else:
        return
        
    try:   
        found = False
        with open(autoexec, mode) as autoexec_file:            
            for line in autoexec_file:
                if ADDON_ID in line:
                    found = True
                    break
    
            if not found and state:
                autoexec_file.seek(0)
                autoexec_file.write('import xbmc\n')
                autoexec_file.write("xbmc.executebuiltin('RunAddon(%s)')\n" % ADDON_ID)
                autoexec_file.truncate()
                
        if not state and found: 
            os.unlink(autoexec)
    except:
        t, v, tb = sys.exc_info()        
        LogToXBMC("Error while write autoexec.py: {0}:{1}.".format(t, v), xbmc.LOGWARNING)
        del tb
        
        

class MyThread(threading.Thread):
    def __init__(self, func, params, back=True):
        threading.Thread.__init__(self)
        self.func = func
        self.params = params
        self.isCanceled = False
        self.daemon = False

    def run(self):
        self.func(self.params)
        
    def stop(self):
        self.isCanceled = True        
        


def showMessage(message='', heading='Torrent-TV.RU', times=6789):
    LogToXBMC('showMessage: %s' % message)
    try: 
        xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s, %s)' % (heading.encode('utf-8'), message.encode('utf-8'), times, ADDON_ICON))
    except Exception, e:
        try: 
            xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s, %s)' % (heading, message, times, ADDON_ICON))
        except Exception, e:            
            LogToXBMC('showMessage: exec failed [%s]' % e, xbmc.LOGWARNING)

def GET(target, post=None, cookie=None):
    t = 0
    monitor = xbmc.Monitor()
    while not monitor.abortRequested() and not closeRequested.isSet():
        t += 1
        try:
            req = urllib2.Request(url=target, data=post)
            req.add_header('User-Agent', 'XBMC (script.torrent-tv.ru)')
            if cookie:
                req.add_header('Cookie', 'PHPSESSID=%s' % cookie)
            resp = urllib2.urlopen(req, timeout=6)
            try:
                http = resp.read()
                return http
            finally:
                resp.close()
            
        except Exception, e:
            if t % 10 == 0:
                LogToXBMC('GET EXCEPT [%s]' % (e), xbmc.LOGERROR)
                monitor.waitForAbort(30)       

def checkPort(params):
        data = GET("http://2ip.ru/check-port/?port=%s" % params)
        beautifulSoup = BeautifulSoup(data)
        port = beautifulSoup.find('div', attrs={'class': 'ip-entry'}).text
        if port.encode('utf-8').find("закрыт") > -1:
            return False
        else:
            return True
        


def tryStringToInt(str_val):
    try:
        return int(str_val)
    except:
        return 0

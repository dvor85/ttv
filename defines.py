﻿import xbmcaddon
import xbmc
import sys
import urllib2
import urllib
import threading
import os
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup

ADDON = xbmcaddon.Addon(id='script.torrent-tv.ru.pp')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_ID = ADDON.getAddonInfo('id')
PTR_FILE = ADDON.getSetting('port_path')
DATA_PATH = xbmc.translatePath(os.path.join("special://profile/addon_data", ADDON_ID))
VERSION = ADDON.getAddonInfo('version')
AUTOSTART = ADDON.getSetting('startlast') == 'true'
DEBUG = ADDON.getSetting('debug') == 'true'
skin = ADDON.getSetting('skin')
SKIN_PATH = ADDON_PATH

print skin
if (skin != None) and (skin != "") and (skin != 'st.anger'):
    SKIN_PATH = DATA_PATH
    

    
def Autostart(state):
    userdata = xbmc.translatePath("special://masterprofile")
    autoexec = os.path.join(userdata, 'autoexec.py')
    if state:
        if os.path.isfile(autoexec): 
            mode = 'r+' 
        else: 
            mode = 'w+'     
        
        try:   
            with open(autoexec, mode) as autoexec_file:
                found = False
                for line in autoexec_file:
                    if ADDON_ID in line:
                        found = True
                        break
        
                if not found:
                    autoexec_file.write('import xbmc\n')
                    autoexec_file.write("xbmc.executebuiltin('RunAddon(%s)')\n" % ADDON_ID)
        except:
            t, v, tb = sys.exc_info()        
            sys.stderr.write("Error while write autoexec.py: {}:{}.".format(t, v))
            del tb
    else:
        if os.path.isfile(autoexec): 
            os.unlink(autoexec)
        

class MyThread(threading.Thread):
    def __init__(self, func, params, back=True):
        threading.Thread.__init__(self)
        self.func = func
        self.params = params
        # self.parent = parent

    def run(self):
        self.func(self.params)
    def stop(self):
        pass

if (sys.platform == 'win32') or (sys.platform == 'win64'):
    ADDON_PATH = ADDON_PATH.decode('utf-8')

def showMessage(message='', heading='Torrent-TV.RU', times=6789):
    try: 
        xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s, %s)' % (heading.encode('utf-8'), message.encode('utf-8'), times, ADDON_ICON))
    except Exception, e:
        try: xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s, %s)' % (heading, message, times, ADDON_ICON))
        except Exception, e:
            xbmc.log('showMessage: exec failed [%s]' % 3)

def GET(target, post=None, cookie=None):
    try:
        print target
        req = urllib2.Request(url=target, data=post)
        req.add_header('User-Agent', 'XBMC (script.torrent-tv.ru)')
        if cookie:
            req.add_header('Cookie', 'PHPSESSID=%s' % cookie)
        resp = urllib2.urlopen(req)
        http = resp.read()
        resp.close()
        return http
    except Exception, e:
        xbmc.log('GET EXCEPT [%s]' % (e), 4)

def checkPort(params):
        data = GET("http://2ip.ru/check-port/?port=%s" % params)
        beautifulSoup = BeautifulSoup(data)
        port = beautifulSoup.find('div', attrs={'class': 'ip-entry'}).text
        if port.encode('utf-8').find("Порт закрыт") > -1:
            return False
        else:
            return True

def tryStringToInt(str_val):
    try:
        return int(str_val)
    except:
        return 0

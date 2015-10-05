# -*- coding: utf-8 -*-
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import xbmcaddon
import xbmc
import sys
import urllib2
import threading
import os
import time
from BeautifulSoup import BeautifulSoup

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_ICON = ADDON.getAddonInfo('icon')
PTR_FILE = ADDON.getSetting('port_path')
DATA_PATH = xbmc.translatePath(os.path.join("special://profile/addon_data", ADDON_ID))
TTV_VERSION = '1.5.3'
AUTOSTART = ADDON.getSetting('autostart') == 'true'
DEBUG = ADDON.getSetting('debug') == 'true'
    
if sys.platform.startswith('win'):
    ADDON_PATH = ADDON_PATH.decode('utf-8')
    DATA_PATH = DATA_PATH.decode('utf-8')

SKIN_PATH = ADDON_PATH
skin = ADDON.getSetting('skin')
if (skin != None) and (skin != "") and (skin != 'st.anger'):
    SKIN_PATH = DATA_PATH

closeRequested = threading.Event()

class Logger():
    
    def __init__(self, tag, minlevel=xbmc.LOGDEBUG):
        self.tag = tag
        self.minlevel = minlevel
        
    def __call__(self, msg, level=xbmc.LOGNOTICE):
        self.log(msg, level)
        
    def log(self, msg, level):
        if level >= self.minlevel:
            try:
                if isinstance(msg, unicode):
                    msg = msg.encode('utf-8', 'ignore')
                m = "[{id}::{tag}] {msg}".format(**{'id':ADDON_ID, 'tag':self.tag, 'msg': msg}).replace(ADDON.getSetting('password'), '********')
                xbmc.log(m, level)
                if DEBUG:
                    m = '{0} {1}'.format(time.strftime('%X'), m)
                    print m  
            except Exception as e:
                xbmc.log('ERROR LOG OUT: {0}'.format(e), xbmc.LOGERROR)      
       
        
    def f(self, msg):
        self.log(msg, xbmc.LOGFATAL)
        
    def e(self, msg):
        self.log(msg, xbmc.LOGERROR)
        
    def w(self, msg):
        self.log(msg, xbmc.LOGWARNING)
            
    def i(self, msg):
        self.log(msg, xbmc.LOGINFO)
        
    def d(self, msg):
        self.log(msg, xbmc.LOGDEBUG)
        
log = Logger('DEFINES')

    
def AutostartViaAutoexec(state):
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
        log.w("Error while write autoexec.py: {0}:{1}.".format(t, v))
        del tb
        
        
class MyThread(threading.Thread):
    def __init__(self, func, *args, **kwargs):
        threading.Thread.__init__(self, target=func, name=func.__name__, args=args)        
        self.daemon = False


def showMessage(message='', heading='Torrent-TV.RU', times=6789):
    log.d('showMessage: %s' % message)
    try: 
        xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s, %s)' % (heading.encode('utf-8'), message.encode('utf-8'), times, ADDON_ICON))
    except Exception, e:
        try: 
            xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s, %s)' % (heading, message, times, ADDON_ICON))
        except Exception, e:            
            log.w('showMessage: exec failed [{0}]'.format(e))
       
       
def isCancel():
    return xbmc.abortRequested or closeRequested.isSet()       
            

def GET(target, post=None, cookie=None, useragent='XBMC (script.torrent-tv.ru)'):
    log.d('try to get: {0}'.format(target))
    t = 0
    req = urllib2.Request(url=target, data=post)
    req.add_header('User-Agent', useragent)
    if post:
        req.add_header("Content-type", "application/x-www-form-urlencoded")
    if cookie:
        req.add_header('Cookie', 'PHPSESSID=%s' % cookie)
    while not isCancel():
        t += 1
        try:
            resp = urllib2.urlopen(req, timeout=6)
            try:
                http = resp.read()
                return http
            finally:
                resp.close()
            
        except Exception, e:
            if t % 10 == 0:
                log.e('GET EXCEPT [{0}]'.format(e))
                if not isCancel():
                    xbmc.sleep(3000)       

def checkPort(*args):
        port = args[0]
        data = GET("http://2ip.ru/check-port/?port=%s" % port)
        beautifulSoup = BeautifulSoup(data)
        bsdata = beautifulSoup.find('div', attrs={'class': 'ip-entry'}).text
        if bsdata.encode('utf-8').find("закрыт") > -1:
            return False
        else:
            return True
        

def tryStringToInt(str_val):
    try:
        return int(str_val)
    except:
        return 0

# -*- coding: utf-8 -*-
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import xbmcaddon
import xbmc
import xbmcgui
import sys
import urllib, urllib2
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
API_MIRROR = ADDON.getSetting('api_mirror')
SITE_MIRROR = '1ttv.org' if API_MIRROR == '1ttvxbmc.top' else 'torrent-tv.ru'
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


def showNotification(msg, icon=ADDON_ICON):
    try:
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8', 'ignore')
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), msg, icon)
    except Exception as e:
        log.e('showNotification error: "{0}"'.format(e))
       
       
def isCancel():
    return xbmc.abortRequested or closeRequested.isSet()      

def AUTH():
    try:        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.99 Safari/537.36',
                   'Content-type': 'application/x-www-form-urlencoded',
                   'Accept-Encoding': 'gzip, deflate'
                   
        }
        cookie = []
#         try:
#             req = urllib2.Request('http://{0}/banhammer/pid'.format(SITE_MIRROR), headers=headers)
#             resp = urllib2.urlopen(req, timeout=6)
#             try:
#                 cookie.append('BHC={0}; path=/;'.format(resp.headers['X-BH-Token']))
#             finally:
#                 resp.close()
#         except Exception as e:
#             log.e('ERROR: open url: {0} {1} '.format(req.get_full_url(), e)) 
            
        
        authdata = {
            'email' : ADDON.getSetting('login'),
            'password' : ADDON.getSetting('password'),
            'remember' : 'on',
            'enter' : 'enter'
        }
#         try:
#             req = urllib2.Request('http://{0}/auth.php'.format(SITE_MIRROR), data=urllib.urlencode(authdata), headers=headers)
#             for coo in cookie:
#                 req.add_header('Cookie', coo)
#             resp = urllib2.urlopen(req, timeout=6)
#             try:
#                 for h in resp.headers.headers:
#                     keyval = h.split(':')
#                     if 'Set-Cookie' in keyval[0]:
#                         cookie.append(keyval[1].strip())
#             finally:
#                 resp.close()
#             
#         except Exception as e:
#             log.e('ERROR: open url: {0} {1} '.format(req.get_full_url(), e))
            
        try:
            req = urllib2.Request('http://{0}/auth.php'.format(SITE_MIRROR), data=urllib.urlencode(authdata), headers=headers)
#             req.add_header('Referer', 'http://{0}/auth.php'.format(SITE_MIRROR))
            for coo in cookie:
                req.add_header('Cookie', coo)
            resp = urllib2.urlopen(req, timeout=6)
            try:
                for h in resp.headers.headers:
                    keyval = h.split(':')
                    if 'Set-Cookie' in keyval[0]:
                        cookie.append(keyval[1].split(';')[0].strip())
            finally:
                resp.close()
            
        except Exception as e:
            log.e('ERROR: open url: {0} {1} '.format(req.get_full_url(), e))
            raise 
            
        return cookie
    except Exception as e:
        log.e('ERROR: {0} on auth'.format(e)) 
        return [] 
            

def GET(target, post=None, cookie=None, headers=None, trys=-1):
    log.d('try to get: {0}'.format(target))
    if not target:
        return
    t = 0
    if not headers:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.99 Safari/537.36'}
    req = urllib2.Request(url=target, data=post, headers=headers)
    
    if post:
        req.add_header("Content-type", "application/x-www-form-urlencoded")
    if cookie:
        for coo in cookie:
            req.add_header('Cookie', coo)
#         req.add_header('Cookie', 'PHPSESSID=%s' % cookie)
    while not isCancel():
        t += 1
        if 0 < trys < t:
            raise Exception('Attempts are over')
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
    try:
        port = args[0]
        data = GET("http://2ip.ru/check-port/?port=%s" % port, trys=2)
        beautifulSoup = BeautifulSoup(data)
        bsdata = beautifulSoup.find('div', attrs={'class': 'ip-entry'}).text
        if bsdata.encode('utf-8').find("закрыт") > -1:
            return False
        else:
            return True
    except Exception as e:
        log.w('checkPort Error: {0}'.format(e))
        

def tryStringToInt(str_val):
    try:
        return int(str_val)
    except:
        return 0

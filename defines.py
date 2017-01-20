# -*- coding: utf-8 -*-
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import xbmcaddon
import xbmc
import xbmcgui
import sys
import threading
import os
import time
from BeautifulSoup import BeautifulSoup
import requests
import utils

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_ICON = ADDON.getAddonInfo('icon')
PTR_FILE = ADDON.getSetting('port_path')
API_MIRROR = ADDON.getSetting('api_mirror')
SITE_MIRROR = '1ttv.org' if API_MIRROR == '1ttvxbmc.top' else 'torrent-tv.ru'
DATA_PATH = xbmc.translatePath(
    os.path.join("special://profile/addon_data", ADDON_ID))
TTV_VERSION = '1.5.3'
AUTOSTART = ADDON.getSetting('autostart') == 'true'
GENDER = ADDON.getSetting('gender')
AGE = ADDON.getSetting('age')
FAVOURITE = ADDON.getSetting('favourite')
DEBUG = ADDON.getSetting('debug') == 'true'

if sys.platform.startswith('win'):
    ADDON_PATH = ADDON_PATH.decode('utf-8')
    DATA_PATH = DATA_PATH.decode('utf-8')

SKIN_PATH = ADDON_PATH
skin = ADDON.getSetting('skin')
if (skin is not None) and (skin != "") and (skin != 'st.anger'):
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
                m = "[{id}::{tag}] {msg}".format(**{'id': ADDON_ID, 'tag': self.tag, 'msg': msg}).replace(
                    ADDON.getSetting('password'), '********')
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
    autoexec = os.path.join(
        xbmc.translatePath("special://masterprofile"), 'autoexec.py')

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
        threading.Thread.__init__(
            self, target=func, name=func.__name__, args=args)
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


def request(url, method='get', params=None, trys=1, **kwargs):
    log.d('try to get: {0}'.format(url))
    if not url:
        return
    t = 0
    kwargs.setdefault('allow_redirects', True)
    kwargs.setdefault('headers', {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) \
            Chrome/45.0.2454.99 Safari/537.36'})
    kwargs.setdefault('timeout', 3.05)

    while not isCancel():
        t += 1
        if 0 < trys < t:
            raise Exception('Attempts are over')
        try:
            r = requests.request(method, url, params=params, **kwargs)
            r.raise_for_status()
            return r

        except Exception as e:
            if t % 10 == 0:
                log.e('GET EXCEPT [{0}]'.format(e))
                if not isCancel():
                    xbmc.sleep(3000)


def checkPort(*args):
    try:
        port = args[0]
        r = request("https://2ip.ru/check-port", params=dict(port=port))
        r.raise_for_status()
        beautifulSoup = BeautifulSoup(r.content)
        bsdata = beautifulSoup.find('div', attrs={'class': 'ip-entry'})
        if utils.utf(bsdata.text).find("закрыт") > -1:
            return False
        else:
            return True
    except Exception as e:
        log.w('checkPort Error: {0}'.format(e))

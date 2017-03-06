# -*- coding: utf-8 -*-
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import xbmcaddon
import xbmc
import xbmcgui
import sys
import threading
import os
import utils
import logger

log = logger.Logger(__name__)
fmt = utils.fmt

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_PATH = utils.true_enc(ADDON.getAddonInfo('path'), 'utf8')
DATA_PATH = utils.true_enc(xbmc.translatePath(os.path.join("special://profile/addon_data", ADDON_ID)), 'utf8')
PTR_FILE = ADDON.getSetting('port_path')
# API_MIRROR = ADDON.getSetting('api_mirror')
# SITE_MIRROR = '1ttv.org' if API_MIRROR == '1ttvxbmc.top' else 'torrent-tv.ru'

# TTV_VERSION = '1.5.3'
AUTOSTART = ADDON.getSetting('autostart') == 'true'
GENDER = ADDON.getSetting('gender')
AGE = ADDON.getSetting('age')
FAVOURITE = ADDON.getSetting('favourite')
DEBUG = ADDON.getSetting('debug') == 'true'

skin = ADDON.getSetting('skin')
if (skin is not None) and (skin != "") and (skin != 'st.anger'):
    SKIN_PATH = DATA_PATH
else:
    SKIN_PATH = ADDON_PATH

closeRequested = threading.Event()


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
        log.w(fmt("Error while write autoexec.py: {0}:{1}.", t, v))
        del tb


class MyThread(threading.Thread):

    def __init__(self, func, *args, **kwargs):
        threading.Thread.__init__(self, target=func, name=func.__name__, args=args, kwargs=kwargs)
        self.daemon = False


def showNotification(msg, icon=ADDON_ICON):
    try:
        msg = utils.utf(msg)
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), msg, icon)
    except Exception as e:
        log.e(fmt('showNotification error: "{0}"', e))


def isCancel():
    return xbmc.abortRequested or closeRequested.isSet()


def request(url, method='get', params=None, trys=3, **kwargs):
    import requests
    params_str = "?" + "&".join((fmt("{0}={1}", *i)
                                 for i in params.iteritems())) if params is not None and method == 'get' else ""
    log.d(fmt('try to get: {url}{params}', url=url, params=params_str))
    if not url:
        return
    kwargs.setdefault('allow_redirects', True)
    kwargs.setdefault('headers', {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) \
            Chrome/45.0.2454.99 Safari/537.36'})
    kwargs.setdefault('timeout', 3.05)
    t = 0
    while not isCancel():
        t += 1
        if 0 < trys < t:
            raise Exception('Attempts are over')
        try:
            r = requests.request(method, url, params=params, **kwargs)
            r.raise_for_status()
            return r
        except Exception as e:
            log.error(fmt('Request error ({t}): {e}', t=t, e=e))
            xbmc.sleep(1000)


def checkPort(*args):
    try:
        from BeautifulSoup import BeautifulSoup
        port = args[0]
        r = request("https://2ip.ru/check-port", params=dict(port=port))
        beautifulSoup = BeautifulSoup(r.content)
        bsdata = beautifulSoup.find('div', attrs={'class': 'ip-entry'})
        if utils.utf(bsdata.text).find("закрыт") > -1:
            return False
        else:
            return True
    except Exception as e:
        log.w(fmt('checkPort Error: {0}', e))

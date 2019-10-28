# -*- coding: utf-8 -*-
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals
from kodi_six import xbmcaddon, xbmc, xbmcgui
import six
import sys
import threading
import os
import utils
import logger
import requests

log = logger.Logger(__name__)

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_PATH = ADDON.getAddonInfo('path')
DATA_PATH = xbmc.translatePath(os.path.join("special://profile/addon_data", ADDON_ID))
CACHE_PATH = xbmc.translatePath(os.path.join("special://temp", ADDON_ID))
PTR_FILE = ADDON.getSetting('port_path')
# API_MIRROR = ADDON.getSetting('api_mirror')
# SITE_MIRROR = '1ttv.org' if API_MIRROR == '1ttvxbmc.top' else 'torrent-tv.ru'

# TTV_VERSION = '1.5.3'
AUTOSTART = ADDON.getSetting('autostart') == 'true'
AUTOSTART_LASTCH = ADDON.getSetting('autostart_lastch') == 'true'
GENDER = ADDON.getSetting('gender')
AGE = ADDON.getSetting('age')
FAVOURITE = ADDON.getSetting('favourite')
DEBUG = ADDON.getSetting('debug') == 'true'
MANUAL_STOP = ADDON.getSetting('manual_stop') == 'true'

skin = ADDON.getSetting('skin')
if (skin is not None) and (skin != "") and (skin != 'st.anger'):
    SKIN_PATH = DATA_PATH
else:
    SKIN_PATH = ADDON_PATH
if not os.path.exists(CACHE_PATH):
    os.makedirs(CACHE_PATH)

closeRequested = threading.Event()
monitor = xbmc.Monitor()


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
        threading.Thread.__init__(self, target=func, name=func.__name__, args=args, kwargs=kwargs)
        self.daemon = False


def showNotification(msg, icon=ADDON_ICON):
    try:
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), msg, icon)
    except Exception as e:
        log.e('showNotification error: "{0}"'.format(e))


def isCancel():
    ret = monitor.abortRequested() or closeRequested.isSet()
#     log.d("isCancel {ret}".format(ret=monitor.abortRequested()))
    return ret


def request(url, method='get', params=None, trys=3, interval=0, session=None, **kwargs):

    params_str = "?" + "&".join(("{0}={1}".format(*i)
                                 for i in params.iteritems())) if params is not None and method == 'get' else ""
    log.d('try to get: {url}{params}'.format(url=url, params=params_str))
    if not url:
        return
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) \
Chrome/45.0.2454.99 Safari/537.36'}
    if 'headers' in kwargs:
        headers.update(kwargs['headers'])
        del kwargs['headers']
    kwargs.setdefault('allow_redirects', True)
    kwargs.setdefault('timeout', 3.05)

    t = 0
    xbmc.sleep(interval)
    while not isCancel():
        t += 1
        if 0 < trys < t:
            raise Exception('Attempts are over')
        try:
            if session:
                r = session.request(method, url, params=params, headers=headers, **kwargs)
            else:
                r = requests.request(method, url, params=params, headers=headers, **kwargs)
            r.raise_for_status()
            return r
        except Exception as e:
            log.error('Request error ({t}): {e}'.format(t=t, e=e))
            xbmc.sleep(interval + 1000)


def platform():
    ret = {
        "arch": sys.maxsize > 2 ** 32 and "x64" or "x86",
    }
    if xbmc.getCondVisibility("system.platform.android"):
        ret["os"] = "android"
        if "arm" in os.uname()[4] or "aarch64" in os.uname()[4]:  # @UndefinedVariable
            ret["arch"] = "arm"
    elif xbmc.getCondVisibility("system.platform.linux"):
        ret["os"] = "linux"
        uname = os.uname()[4]  # @UndefinedVariable
        if "arm" in uname:
            if "armv7" in uname:
                ret["arch"] = "armv7"
            elif "armv6" in uname:
                ret["arch"] = "armv6"
            else:
                ret["arch"] = "arm"
        elif "mips" in uname:
            if sys.maxunicode > 65536:
                ret["arch"] = 'mipsel_ucs4'
            else:
                ret["arch"] = 'mipsel_ucs2'
        elif "aarch64" in uname:
            if six.MAXSIZE > 2147483647:  # is_64bit_system
                if sys.maxunicode > 65536:
                    ret["arch"] = 'aarch64_ucs4'
                else:
                    ret["arch"] = 'aarch64_ucs2'
            else:
                ret["arch"] = "armv7"  # 32-bit userspace
    elif xbmc.getCondVisibility("system.platform.windows"):
        ret["os"] = "windows"
    elif xbmc.getCondVisibility("system.platform.osx"):
        ret["os"] = "darwin"
    elif xbmc.getCondVisibility("system.platform.ios"):
        ret["os"] = "ios"
        ret["arch"] = "arm"

    return ret

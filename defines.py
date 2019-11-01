# -*- coding: utf-8 -*-
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import os
import sys
import threading

import requests
import six
import xbmcaddon
import xbmc
import xbmcgui
from six import iteritems
from utils import uni, str2

import logger

log = logger.Logger(__name__)

ADDON = xbmcaddon.Addon()
ADDON_ID = uni(ADDON.getAddonInfo('id'))
ADDON_ICON = uni(ADDON.getAddonInfo('icon'))
ADDON_PATH = uni(ADDON.getAddonInfo('path'))
DATA_PATH = uni(xbmc.translatePath(str2(os.path.join("special://profile/addon_data", ADDON_ID))))
CACHE_PATH = uni(xbmc.translatePath(str2(os.path.join("special://temp", ADDON_ID))))
PTR_FILE = uni(ADDON.getSetting('port_path'))
AUTOSTART = uni(ADDON.getSetting('autostart')) == 'true'
AUTOSTART_LASTCH = uni(ADDON.getSetting('autostart_lastch')) == 'true'
GENDER = uni(ADDON.getSetting('gender'))
AGE = uni(ADDON.getSetting('age'))
FAVOURITE = uni(ADDON.getSetting('favourite'))
DEBUG = uni(ADDON.getSetting('debug')) == 'true'
MANUAL_STOP = uni(ADDON.getSetting('manual_stop')) == 'true'
SKIN_PATH = ADDON_PATH
if not os.path.exists(CACHE_PATH):
    os.makedirs(CACHE_PATH)

closeRequested = threading.Event()
monitor = xbmc.Monitor()


class MyThread(threading.Thread):

    def __init__(self, func, *args, **kwargs):
        threading.Thread.__init__(self, target=func, name=func.__name__, args=args, kwargs=kwargs)
        self.daemon = False


def showNotification(msg, icon=ADDON_ICON):
    try:
        xbmcgui.Dialog().notification(str2(ADDON.getAddonInfo('name')), str2(msg), str2(icon))
    except Exception as e:
        log.e('showNotification error: "{0}"'.format(uni(e)))


def isCancel():
    ret = monitor.abortRequested() or closeRequested.isSet()
    return ret


def request(url, method='get', params=None, trys=3, interval=0, session=None, **kwargs):
    params_str = "?" + "&".join(("{0}={1}".format(*i)
                                 for i in iteritems(params))) if params is not None and method == 'get' else ""
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

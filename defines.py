# -*- coding: utf-8 -*-
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru


import os
import sys
import threading

import requests
import urllib3
import six
import xbmcaddon
import xbmc
import xbmcgui
from xbmcvfs import translatePath
from six.moves import UserDict
from pathlib import Path

import logger

log = logger.Logger(__name__)

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_PATH = ADDON.getAddonInfo('path')
DATA_PATH = Path(translatePath("special://profile/addon_data"), ADDON_ID)
CACHE_PATH = Path(translatePath("special://temp"), ADDON_ID)
PTR_FILE = ADDON.getSetting('port_path')
AUTOSTART = ADDON.getSetting('autostart') == 'true'
AUTOSTART_LASTCH = ADDON.getSetting('autostart_lastch') == 'true'
GENDER = ADDON.getSetting('gender')
AGE = ADDON.getSetting('age')
FAVOURITE = ADDON.getSetting('favourite')
DEBUG = ADDON.getSetting('debug') == 'true'
PROXY_TYPE, _proxy_addr, _port = urllib3.get_host(ADDON.getSetting('pomoyka_proxy'))
PROXY_TYPE = ADDON.getSetting('proxy_type')
if PROXY_TYPE == 'socks5':
    PROXY_TYPE = 'socks5h'
PROXIES = {"http": f"{PROXY_TYPE}://{_proxy_addr}:{_port}",
           "https": f"{PROXY_TYPE}://{_proxy_addr}:{_port}"}
Path(CACHE_PATH).mkdir(parents=True, exist_ok=True)
closeRequested = threading.Event()
monitor = xbmc.Monitor()


class MyThread(threading.Thread):

    def __init__(self, func, *args, **kwargs):
        threading.Thread.__init__(self, target=func, name=func.__name__, args=args, kwargs=kwargs)
        self.daemon = False

    def start(self):
        threading.Thread.start(self)
        return self


class Timers(UserDict):
    def __init__(self, *args, **kwargs):
        UserDict.__init__(self, *args, **kwargs)
        self.data = {}
        pass

    def start(self, name, timer):
        if not isCancel():
            timer.name = name
            timer.daemon = False
            timer.start()
            log.d('start timer "{name}"'.format(name=name))
            self.data[name] = timer

    def stop(self, name):
        if self.data.get(name):
            self.data[name].cancel()
            log.d('stop timer "{name}"'.format(name=name))
            self.data[name] = None


def showNotification(msg, icon=ADDON_ICON):
    try:
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), msg, icon)
    except Exception as e:
        log.e(f'showNotification error: "{e}"')


def isCancel():
    ret = monitor.abortRequested() or closeRequested.isSet()
    return ret


def request(url, method='get', params=None, trys=3, interval=0, session=None, proxies=None, **kwargs):
    params_str = "?" + "&".join(f"{k}={v}" for k, v in params.items()) if params is not None and method == 'get' else ""
    if proxies is None and ADDON.getSetting('pomoyka_proxy_for_all') == 'true':
        proxies = PROXIES
    log.d(f'try to get: {url}{params_str}')
    log.d(f'proxies: {proxies}')
    if not url:
        return
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.99 Safari/537.36'}
    if 'headers' in kwargs:
        headers.update(kwargs['headers'])
        del kwargs['headers']
    kwargs.setdefault('allow_redirects', True)
    kwargs.setdefault('timeout', 10.05)

    t = 0
    xbmc.sleep(interval)
    while not isCancel():
        t += 1
        if 0 < trys < t:
            raise Exception('Attempts are over')
        try:
            if session:
                r = session.request(method, url, params=params, headers=headers, proxies=proxies, **kwargs)
            else:
                r = requests.request(method, url, params=params, headers=headers, proxies=proxies, **kwargs)
            r.raise_for_status()
            return r
        except Exception as e:
            log.error(f'Request error ({t}): {e}')
            xbmc.sleep(interval + 1000)


def platform():
    ret = {
        "arch": six.MAXSIZE > 2 ** 32 and "x64" or "x86",
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
            if six.MAXSIZE > 2 ** 32:  # is_64bit_system
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

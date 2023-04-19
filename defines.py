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
from contextlib import contextmanager

import logger

log = logger.Logger(__name__)

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_PATH = ADDON.getAddonInfo('path')
DATA_PATH = Path(translatePath("special://profile/addon_data"), ADDON_ID)
CACHE_PATH = Path(translatePath("special://temp"), ADDON_ID)
PTR_FILE = ADDON.getSetting('port_path')
AUTOSTART = ADDON.getSettingBool('autostart')
AUTOSTART_LASTCH = ADDON.getSettingBool('autostart_lastch')
GENDER = ADDON.getSettingInt('gender')
AGE = ADDON.getSettingInt('age')
FAVOURITE = ADDON.getSetting('favourite')
DEBUG = ADDON.getSettingBool('debug')
PROXY_ADDR_PORT = ADDON.getSetting('proxy_addr_port').split(':')
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


@contextmanager
def progress_dialog(message):
    pd = xbmcgui.DialogProgress()
    pd.create(heading=ADDON.getAddonInfo('name'), message=message)
    try:
        yield pd
    finally:
        pd.close()


@contextmanager
def progress_dialog_bg(message):
    pd = xbmcgui.DialogProgressBG()
    pd.create(heading=ADDON.getAddonInfo('name'), message=message)
    try:
        yield pd
    finally:
        pd.close()


def showNotification(message, heading=ADDON.getAddonInfo('name'), icon=ADDON_ICON, timeout=5000):
    try:
        xbmcgui.Dialog().notification(heading=heading, message=message, icon=icon, time=timeout)
        log.d(message)
    except Exception as e:
        log.e(f'showNotification error: "{e}"')


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
            log.d(f'start timer "{name}"')
            self.data[name] = timer

    def stop(self, name):
        if self.data.get(name):
            self.data[name].cancel()
            log.d(f'stop timer "{name}"')
            self.data[name] = None


def isCancel():
    return monitor.abortRequested() or closeRequested.isSet()


def request(url, method='get', params=None, trys=1, interval=0.01, session=None, proxies=None, **kwargs):
    if url:
        params_str = "?" + "&".join(f"{k}={v}" for k, v in params.items()) if params is not None and method == 'get' else ""
        if proxies is None and ADDON.getSettingBool('pomoyka_proxy_for_all'):
            proxies = PROXIES
        log.d(f'try to get: {url}{params_str}')
        log.d(f'proxies: {proxies}')

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.99 Safari/537.36'}
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
            del kwargs['headers']
        kwargs.setdefault('allow_redirects', True)
        kwargs.setdefault('timeout', 10.05)
        for t in range(trys):
            monitor.waitForAbort(interval)
            if not isCancel():
                try:
                    if session:
                        r = session.request(method, url, params=params, headers=headers, proxies=proxies, **kwargs)
                    else:
                        r = requests.request(method, url, params=params, headers=headers, proxies=proxies, **kwargs)
                    r.raise_for_status()
                    return r

                except Exception as e:
                    log.error(f'Request error ({t+1}): {e}')

        raise TimeoutError(f'Attempts of request of "{url}" are over')


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

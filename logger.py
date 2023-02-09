# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import xbmc
import time
import defines


class Logger:

    def __init__(self, tag, minlevel=xbmc.LOGDEBUG):
        self.tag = tag
        self.minlevel = minlevel

    def __call__(self, msg, level=xbmc.LOGINFO):
        self.log(msg, level)

    def log(self, msg, level):
        if level >= self.minlevel:
            try:
                m = f"[{defines.ADDON_ID}::{self.tag}] {msg}"
                xbmc.log(m, level)
                if defines.DEBUG:
                    m = f'{time.strftime("%X")} {m}'
                    print(m)
            except Exception as e:
                xbmc.log(f'ERROR LOG OUT: {e}', xbmc.LOGERROR)

    def notice(self, msg):
        return self.__call__(msg)

    def f(self, msg):
        self.log(msg, xbmc.LOGFATAL)

    def fatal(self, msg):
        return self.f(msg)

    def e(self, msg):
        self.log(msg, xbmc.LOGERROR)

    def error(self, msg):
        return self.e(msg)

    def w(self, msg):
        self.log(msg, xbmc.LOGWARNING)

    def warn(self, msg):
        return self.w(msg)

    def i(self, msg):
        self.log(msg, xbmc.LOGINFO)

    def info(self, msg):
        return self.i(msg)

    def d(self, msg):
        self.log(msg, xbmc.LOGDEBUG)

    def debug(self, msg):
        return self.d(msg)

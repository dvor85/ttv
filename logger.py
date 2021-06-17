# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import print_function, absolute_import, division, unicode_literals
from utils import uni, str2
import xbmc
import time
import defines


class Logger:

    def __init__(self, tag, minlevel=xbmc.LOGDEBUG):
        self.tag = uni(tag)
        self.minlevel = minlevel

    def __call__(self, msg, level=xbmc.LOGINFO):
        self.log(msg, level)

    def log(self, msg, level):
        if level >= self.minlevel:
            try:
                m = "[{id}::{tag}] {msg}".format(id=defines.ADDON_ID, tag=self.tag, msg=uni(msg))
                xbmc.log(str2(m), level)
                if defines.DEBUG:
                    m = '{0} {1}'.format(uni(time.strftime('%X')), m)
                    print(str2(m))
            except Exception as e:
                xbmc.log(str2('ERROR LOG OUT: {0}').format(str2(e)), xbmc.LOGERROR)

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

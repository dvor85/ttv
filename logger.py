# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from kodi_six import xbmc
import utils
import six
import defines
import time


# fmt = utils.fmt


class Logger():

    def __init__(self, tag, minlevel=xbmc.LOGDEBUG):
        self.tag = tag
        self.minlevel = minlevel

    def __call__(self, msg, level=xbmc.LOGNOTICE):
        self.log(msg, level)

    def log(self, msg, level):
        if level >= self.minlevel:
            try:
                m = "[{id}::{tag}] {msg}".format(id=defines.ADDON_ID, tag=self.tag, msg=six.ensure_text(msg).replace(
                    defines.ADDON.getSetting('password'), '********'))

                xbmc.log(m, level)
                if defines.DEBUG:
                    m = '{0} {1}'.format(time.strftime('%X'), m)
                    print m
            except Exception as e:
                xbmc.log('ERROR LOG OUT: {0}'.format(e), xbmc.LOGERROR)

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

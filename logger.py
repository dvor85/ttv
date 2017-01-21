# -*- coding: utf-8 -*-

import xbmc
import utils
import defines
import time


class Logger():

    def __init__(self, tag, minlevel=xbmc.LOGDEBUG):
        self.tag = tag
        self.minlevel = minlevel

    def __call__(self, msg, level=xbmc.LOGNOTICE):
        self.log(msg, level)

    def log(self, msg, level):
        if level >= self.minlevel:
            try:
                msg = utils.utf(msg)
                m = "[{id}::{tag}] {msg}".format(**{'id': defines.ADDON_ID, 'tag': self.tag, 'msg': msg}).replace(
                    defines.ADDON.getSetting('password'), '********')
                xbmc.log(m, level)
                if defines.DEBUG:
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

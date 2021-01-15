# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import json
import os
import time

import defines
import logger
from .tchannel import TChannel, TChannels
from utils import uni, fs_str

log = logger.Logger(__name__)


class Channel(TChannel):

    def __init__(self, data=None):
        TChannel.__init__(self, data=data, src='allfon', player='ace', mode='PID')
        if data is None:
            data = {}
        self.data['cat'] = None


class Channels(TChannels):

    def __init__(self, lock):
        self.url = 'http://{pomoyka}/trash/ttv-list/allfon.json'.format(pomoyka=uni(defines.ADDON.getSetting('pomoyka_domain')))
        self._temp = self._temp = os.path.join(defines.CACHE_PATH, "allfon.json")
        TChannels.__init__(self, name='allfon', reload_interval=1800, lock=lock)

    def _load_jdata(self):
        log.d('get {temp}'.format(temp=self._temp))
        if os.path.exists(fs_str(self._temp)):
            if time.time() - os.path.getmtime(fs_str(self._temp)) <= self.reload_interval:
                with open(fs_str(self._temp), 'r') as fp:
                    return json.load(fp)

    def _save_jdata(self, jdata):
        with open(fs_str(self._temp), 'wb') as fp:
            json.dump(jdata, fp)

    def update_channels(self):
        TChannels.update_channels(self)
        jdata = dict()
        try:
            jdata = self._load_jdata()
            if not jdata:
                raise Exception("{temp} is empty".format(temp=self._temp))

        except Exception as e:
            log.debug("load_json_temp error: {0}".format(uni(e)))
            try:
                with self.lock:
                    r = defines.request(self.url, proxies=defines.PROXIES, interval=3000)
                jdata = r.json()
                self._save_jdata(jdata)
            except Exception as e:
                log.error("get_channels error: {0}".format(uni(e)))
                log.i('Try to load previos channels, if availible')
                try:
                    jdata = self._load_jdata(False)
                    if not jdata:
                        raise Exception("Channels are not avalible")
                except Exception as e:
                    log.error(uni(e))

        if jdata:
            chs = jdata.get('channels', [])
            for ch in chs:
                self.channels.append(Channel(ch))

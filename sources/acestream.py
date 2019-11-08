# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import json
import os
import time
from utils import uni, str2, str2int

import defines
import logger
from .tchannel import TChannel, TChannels

log = logger.Logger(__name__)


class Channels(TChannels):

    def __init__(self, prior=0):
        self.url = 'http://{pomoyka}/trash/ttv-list/ace.json'.format(pomoyka=uni(defines.ADDON.getSetting('pomoyka_domain')))
        self._temp = os.path.join(defines.CACHE_PATH, "ace.json")
        TChannels.__init__(self, reload_interval=1800, prior=prior)

    def _load_jdata(self):
        log.d('get {temp}'.format(temp=self._temp))
        if os.path.exists(self._temp):
            if time.time() - os.path.getmtime(self._temp) <= self.reload_interval:
                with open(self._temp, 'r') as fp:
                    return json.load(fp)

    def _save_jdata(self, jdata):
        with open(self._temp, 'wb') as fp:
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
                r = defines.request(self.url, interval=3000)
                jdata = r.json()
                self._save_jdata(jdata)
            except Exception as e:
                log.error("get_channels error: {0}".format(uni(e)))

        chs = jdata.get('channels', [])
        for ch in chs:
            self.channels.append(TChannel(ch, src='acestream', player='ace'))

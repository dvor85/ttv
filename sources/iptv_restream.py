# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import json
import gzip
import os
import time
from utils import uni, fs_str

import defines
import logger
from .tchannel import TChannel, TChannels

log = logger.Logger(__name__)


class Channel(TChannel):

    def __init__(self, data={}):
        TChannel.__init__(self, data=data, src='iptv', player='tsp')
        self.data['cat'] = self.data.get('category')


class Channels(TChannels):

    def __init__(self):
        self.url = 'https://iptv-org.github.io/iptv/channels.json'
        self._temp = os.path.join(defines.CACHE_PATH, "iptv_restream.json.gz")
        TChannels.__init__(self, name='iptv', reload_interval=86400)

    def _load_jdata(self, avail=True):
        log.d('get {temp}'.format(temp=self._temp))
        if os.path.exists(fs_str(self._temp)):
            if not avail or (time.time() - os.path.getmtime(fs_str(self._temp)) <= self.reload_interval):
                with gzip.open(fs_str(self._temp), 'r') as fp:
                    return json.load(fp)

    def _save_jdata(self, jdata):
        with gzip.open(fs_str(self._temp), 'w') as fp:
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
                log.i('Try to load previos channels, if availible')
                try:
                    jdata = self._load_jdata(False)
                    if not jdata:
                        raise Exception("Channels are not avalible")
                except Exception as e:
                    log.error(uni(e))

        if jdata:
            for ch in jdata:
                if len([c for c in ch.get('languages', []) if 'rus' == c.get('code')]) > 0:
                    self.channels.append(Channel(ch))

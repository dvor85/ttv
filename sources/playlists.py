# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import os
import time
from utils import uni, fs_str
import m3u8

import defines
import logger
from .tchannel import TChannel, TChannels

log = logger.Logger(__name__)


class Channel(TChannel):

    def __init__(self, data={}):
        TChannel.__init__(self, data=data, src='playlists', player='tsp')
        # self.data['cat'] = self.data.get('category')


class Channels(TChannels):

    def __init__(self):

        self.urls = uni(defines.ADDON.getSetting('playlists_urls')).split(';')
        self._temp = os.path.join(defines.CACHE_PATH, "playlist.m3u")
        self.proxies = defines.PROXIES if defines.ADDON.getSetting('playlists_use_proxy') == 'true' else None
        TChannels.__init__(self, name='playlists', reload_interval=86400)

    def _load_playlist(self, avail=True):
        log.d('get {temp}'.format(temp=self._temp))
        if os.path.exists(fs_str(self._temp)):
            if not avail or (time.time() - os.path.getmtime(fs_str(self._temp)) <= self.reload_interval):
                return m3u8.load(fs_str(self._temp))

    def _save_jdata(self, data):
        data.dump(fs_str(self._temp))

    def update_channels(self):
        TChannels.update_channels(self)
        for url in self.urls:
            self._temp = os.path.join(defines.CACHE_PATH, os.path.basename(url))
            data = {}
            try:
                data = self._load_playlist()
                if not data:
                    raise Exception("{temp} is empty".format(temp=self._temp))

            except Exception as e:
                log.debug("load error: {0}".format(uni(e)))
                try:
                    data = m3u8.load(url)
                    r = defines.request(url, interval=3000, proxies=self.proxies)
                    r.raise_for_status()
                    data = m3u8.loads(r.content)
                    self._save_jdata(data)

                except Exception as e:
                    log.error("get_channels error: {0}".format(uni(e)))
                    log.i('Try to load previos channels, if availible')
                    try:
                        data = self._load_playlist(False)
                        if not data:
                            raise Exception("Channels are not avalible")
                    except Exception as e:
                        log.error(uni(e))

            if data:
                ch = {}
                for seg in data.segments:
                    ch["url"] = seg.uri
                    ch["name"] = seg.title
                    ch["cat"] = seg.group

                    self.channels.append(Channel(ch))

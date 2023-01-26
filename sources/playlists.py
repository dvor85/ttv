# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import time
from utils import uni
import m3u8  # @UnresolvedImport
from pathlib import Path

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
        self._temp = Path(defines.CACHE_PATH, "playlist.m3u")
        self.proxies = defines.PROXIES if defines.ADDON.getSetting('playlists_use_proxy') == 'true' else None
        TChannels.__init__(self, name='playlists', reload_interval=86400)

    def _load_playlist(self, avail=True):
        log.d(f'get {self._temp}')
        if self._temp.exists():
            if not avail or (time.time() - self._temp.stat().st_mtime <= self.reload_interval):
                return m3u8.load(str(self._temp))

    def _save_jdata(self, data):
        data.dump(str(self._temp))

    def update_channels(self):
        TChannels.update_channels(self)
        for url in self.urls:
            self._temp = Path(defines.CACHE_PATH, Path(url).name)
            data = {}
            try:
                data = self._load_playlist()
                if not data:
                    raise Exception(f"{self._temp} is empty")

            except Exception as e:
                log.debug(f"load error: {e}")
                try:
                    if not Path(url).exists():
                        r = defines.request(url, interval=3000, proxies=self.proxies)
                        if r.ok:
                            data = m3u8.loads(r.text)
                            self._save_jdata(data)
                    else:
                        data = m3u8.load(url)

                except Exception as e:
                    log.error(f"get_channels error: {e}")
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

# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import time
from pathlib import Path
import re

import defines
import logger
from .tchannel import TChannel, TChannels

log = logger.Logger(__name__)
_re_m3u = re.compile(r'(?P<tag>[^\s="]+)="(?P<val>[^"]+)"')
_re_notprintable = re.compile(r'[^A-Za-zА-Яа-я0-9\+\-\_\(\)\s\.\:\/\*\\|\\\&\%\$\@\!\~\;]')


class Channel(TChannel):

    def __init__(self, data={}):
        TChannel.__init__(self, data=data, src='playlists', player='tsp')
        if self.data.get('group-title'):
            self.data['cat'] = self.data['group-title']
        self.data['title'] = _re_notprintable.sub('', self.data['title']).strip().capitalize()
        self.data['name'] = _re_notprintable.sub('', self.data['name']).strip().capitalize()


class Channels(TChannels):

    def __init__(self):

        self.urls = defines.ADDON.getSetting('playlists_urls').split(';')
        self.proxies = defines.PROXIES if defines.ADDON.getSetting('playlists_use_proxy') == 'true' else None
        TChannels.__init__(self, name='playlists', reload_interval=86400)

    def _load_playlist(self, filename, avail=True):
        log.d(f'get {filename}')
        if filename.exists():
            if not avail or (time.time() - filename.stat().st_mtime <= self.reload_interval):
                return self.parse_m3u(filename)
        else:
            log.w(f'{filename} not exists in cache')

    def parse_m3u(self, filename):
        ret = []
        lines = []
        if Path(filename).exists():
            lines = Path(filename).read_text().splitlines()
        else:
            r = defines.request(filename, interval=3, proxies=self.proxies)
            if r.ok:
                lines = r.text.splitlines()
                filename.write_bytes(r.content)

        for line in lines:
            if line.startswith("#"):
                if line != "#EXTM3U":
                    seg = {k.replace('tvg-', ''): v for k, v in _re_m3u.findall(line)}
                    seg['title'] = line.rsplit(',', 1)[-1]

                    if 'name' in seg:
                        ret.append(seg)
            elif ret:
                ret[-1]['url'] = line
                ret[-1].setdefault('name', Path(line).name)
        return ret

    def update_channels(self):
        TChannels.update_channels(self)
        for url in self.urls:
            fn = Path(defines.CACHE_PATH, Path(url).name)
            data = {}
            try:
                data = self._load_playlist(fn)

                if not data:
                    data = self.parse_m3u(url)

                if not data:
                    log.i('Try to load previos channels, if availible')
                    data = self._load_playlist(fn, False)

                if not data:
                    log.w(f"Channels are not avalible in {fn}")
            except Exception as e:
                log.error(e)

            if data:
                self.channels.extend(Channel(ch) for ch in data)

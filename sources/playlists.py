# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import time
from pathlib import Path
import re

import defines
import logger
from .tchannel import TChannel, TChannels

log = logger.Logger(__name__)
_re_notprintable = re.compile(r'[^A-Za-zА-Яа-я0-9\+\-\_\(\)\s\.\:\/\*\\|\\\&\%\$\@\!\~\;]')


class Channel(TChannel):

    def __init__(self, data={}):
        TChannel.__init__(self, data=data, src='playlists', player='tsp')
        self.data['cat'] = self.data.get('group-title')
#         self.data['title'] = _re_notprintable.sub('', self.data['title']).strip().capitalize()
        self.data['name'] = _re_notprintable.sub('', self.data['name']).strip().capitalize()


class Channels(TChannels):

    def __init__(self):

        self.urls = defines.ADDON.getSetting('playlists_urls').split(';')
        self.proxies = defines.PROXIES if defines.ADDON.getSettingBool('playlists_use_proxy') else None
        TChannels.__init__(self, name='playlists', reload_interval=86400)

    def _load_playlist(self, filename, avail=True):
        log.d(f'get {filename}')
        if filename.exists():
            if not avail or (time.time() - filename.stat().st_mtime <= self.reload_interval):
                return self.parse_m3u(filename)
        else:
            log.w(f'{filename} not exists in cache')

    def parse_m3u(self, url):
        _re_m3u = re.compile(r'(?P<tag>[^\s="]+)="(?P<val>[^"]+)"')
        ret = []
        lines = []
        if Path(url).exists():
            lines = Path(url).read_text().splitlines()
        elif '://' in url:
            r = defines.request(url, interval=3, proxies=self.proxies)
            if r.ok:
                lines = r.text.splitlines()
                Path(defines.CACHE_PATH, Path(url).name).write_bytes(r.content)
        else:
            lines = url.splitlines()

        group_title = None
        for line in lines:
#             log.d(line)
            if line.startswith("#"):
                if line != "#EXTM3U":
                    seg = {k.replace('tvg-', ''): v for k, v in _re_m3u.findall(line)}
                    seg['name'] = line.rsplit(',', 1)[-1]
                    if seg.get('group-title'):
                        group_title = seg['group-title']
                    elif group_title:
                        seg['group-title'] = group_title
                    if seg.get('name') and '://' not in seg['name']:
                        ret.append(seg)
#                     log.d(f"{seg}")
            elif line.strip() and ret:
                ret[-1]['url'] = line.strip()
        return ret

    def update_channels(self):
        self.channels.clear()
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

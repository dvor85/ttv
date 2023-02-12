# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import json
import time
from pathlib import Path

import defines
import logger
from .tchannel import TChannel, TChannels

log = logger.Logger(__name__)


class Channel(TChannel):

    def __init__(self, data={}):
        TChannel.__init__(self, data=data, src='iptv', player='tsp')
        self.data['cat'] = self.data['categories'][0] if self.data.get('categories') else self.src()
        if self.data.get('alt_names'):
            self.data['name'] = self.data['alt_names'][0]


class Channels(TChannels):

    def __init__(self):
        self.url = {'channels': 'https://iptv-org.github.io/api/channels.json',
                    'streams': 'https://iptv-org.github.io/api/streams.json'}
        self._temp = Path(defines.CACHE_PATH, "iptv_org.json")
        TChannels.__init__(self, name='iptv', reload_interval=86400)

    def _load_jdata(self, avail=True):
        log.d(f'get {self._temp}')
        if self._temp.exists():
            if not avail or (time.time() - self._temp.stat().st_mtime <= self.reload_interval):
                with self._temp.open(mode='r') as fp:
                    return json.load(fp)
        else:
            log.w(f'{self._temp} not exists in cache')

    def _save_jdata(self, jdata):
        with self._temp.open(mode='w') as fp:
            json.dump(jdata, fp)

    def update_channels(self):
        TChannels.update_channels(self)
        jdata = []
        try:
            jdata = self._load_jdata()
            if not jdata:
                r = defines.request(self.url['channels'], interval=3000)
                jchannels = r.json()
                r = defines.request(self.url['streams'], interval=3000)
                jstreams = r.json()
                for ch in jchannels:
                    if "rus" in ch.get('languages', []):
                        [ch.update(st) for st in jstreams if st['channel'] == ch['id']]
                        if 'url' in ch and ch['status'] in {"online", "timeout"}:
                            jdata.append(ch)

                self._save_jdata(jdata)

            if not jdata:
                log.i('Try to load previos channels, if availible')
                jdata = self._load_jdata(False)

            if not jdata:
                log.w("Channels are not avalible")
        except Exception as e:
            log.error(e)

        if jdata:
            self.channels.extend(Channel(_j) for _j in jdata)

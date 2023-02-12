# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru


import json
import time

import defines
import logger
from pathlib import Path
from .tchannel import TChannel, TChannels

log = logger.Logger(__name__)


class Channel(TChannel):

    def __init__(self, data=None):
        TChannel.__init__(self, data=data, src='acetv', player='ace', mode='PID')
        if data is None:
            data = {}
        self.data['cat'] = None


class Channels(TChannels):

    def __init__(self, lock):
        self.url = 'http://{pomoyka}/trash/ttv-list/acetv.json'.format(pomoyka=defines.ADDON.getSetting('pomoyka_domain'))
        self._temp = Path(defines.CACHE_PATH, Path(self.url).name)
        TChannels.__init__(self, name='acetv', reload_interval=3600, lock=lock)

    def _load_jdata(self, avail=True):
        log.d(f'get {self._temp}')
        if self._temp.exists():
            if not avail or (time.time() - self._temp.stat().st_mtime <= self.reload_interval):
                with self._temp.open(mode='r') as fp:
                    return json.load(fp)
        else:
            log.w(f"{self._temp} not exists")

    def _save_jdata(self, jdata):
        with self._temp.open(mode='w+') as fp:
            json.dump(jdata, fp)

    def update_channels(self):
        TChannels.update_channels(self)
        jdata = dict()
        try:
            jdata = self._load_jdata()
            if not jdata:
                with self.lock:
                    r = defines.request(self.url, proxies=defines.PROXIES, interval=3000)
                jdata = r.json()
                self._save_jdata(jdata)
            if not jdata:
                log.i('Try to load previos channels, if availible')
                jdata = self._load_jdata(False)
                if not jdata:
                    log.w("Channels are not avalible")
        except Exception as e:
            log.error(e)

        if jdata:
            self.channels.extend(Channel(ch) for ch in jdata.get('channels', []))

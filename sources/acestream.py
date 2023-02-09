# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import json
import time

import defines
import logger
from .tchannel import TChannel, TChannels
from pathlib import Path
log = logger.Logger(__name__)


class Channels(TChannels):

    def __init__(self, lock):
        self.url = 'http://{pomoyka}/trash/ttv-list/ace.json'.format(pomoyka=defines.ADDON.getSetting('pomoyka_domain'))
        self._temp = Path(defines.CACHE_PATH, Path(self.url).name)
        TChannels.__init__(self, name='acestream', reload_interval=3600, lock=lock)

    def _load_jdata(self, avail=True):
        log.d('get {temp}'.format(temp=self._temp))
        if self._temp.exists():
            if not avail or (time.time() - self._temp.stat().st_mtime <= self.reload_interval):
                with self._temp.open(mode='r') as fp:
                    return json.load(fp)

    def _save_jdata(self, jdata):
        with self._temp.open(mode='w+') as fp:
            json.dump(jdata, fp)

    def update_channels(self):
        TChannels.update_channels(self)
        jdata = dict()
        try:
            jdata = self._load_jdata()
            if not jdata:
                raise Exception(f"{self._temp} is empty")

        except Exception as e:
            log.debug(f"load_json_temp error: {e}")
            try:
                with self.lock:
                    r = defines.request(self.url, proxies=defines.PROXIES, interval=3000)
                jdata = r.json()
                self._save_jdata(jdata)
            except Exception as e:
                log.error(f"get_channels error: {e}")
                log.i('Try to load previos channels, if availible')
                try:
                    jdata = self._load_jdata(False)
                    if not jdata:
                        raise Exception("Channels are not avalible")
                except Exception as e:
                    log.error(e)

        if jdata:
            self.channels.extend(TChannel(ch, src='acestream', player='ace', mode='PID') for ch in jdata.get('channels', []))

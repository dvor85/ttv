# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import utils
import defines
import logger
from tchannel import TChannel, TChannels
import os
import time
import json

log = logger.Logger(__name__)
fmt = utils.fmt


class Channel(TChannel):

    def get_id(self):
        return TChannel.get_name(self)


class Channels(TChannels):

    def __init__(self):
        self.url = fmt('http://{pomoyka}/trash/ttv-list/ace.json', pomoyka=defines.ADDON.getSetting('pomoyka_domain'))
        self._temp = os.path.join(defines.CACHE_PATH, "ace.json")
        TChannels.__init__(self, reload_interval=1800)

    def _load_jdata(self):
        log.d(fmt('get {temp}', temp=self._temp))
        if os.path.exists(self._temp):
            if time.time() - os.path.getmtime(self._temp) <= self.reload_interval:
                with open(self._temp, 'r') as fp:
                    return json.load(fp)

    def _save_jdata(self, jdata):
        with open(self._temp, 'wb') as fp:
            json.dump(jdata, fp)

    def update_channels(self):
        TChannels.update_channels(self)
        try:
            jdata = self._load_jdata()
            if not jdata:
                raise Exception(fmt("{temp} is empty", temp=self._temp))

        except Exception as e:
            log.debug(fmt("load_json_temp error: {0}", e))
            try:
                r = defines.request(self.url, interval=3000)
                jdata = r.json()
                self._save_jdata(jdata)
            except Exception as e:
                log.error(fmt("get_channels error: {0}", e))

        chs = jdata.get('channels', [])
        for ch in chs:
            self.channels.append(Channel(ch))

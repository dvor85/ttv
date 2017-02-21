# -*- coding: utf-8 -*-

import utils
import defines
import logger
from tchannel import TChannel

log = logger.Logger(__name__)
fmt = utils.fmt


class PomoykaChannel(TChannel):

    def get_id(self):
        return TChannel.get_name(self)


class Pomoyka():

    def __init__(self):
        self.url = 'http://super-pomoyka.us.to/trash/ttv-list/ttv.json'
        self.channels = []

    def get_channels(self):
        try:
            r = defines.request(self.url)
            jdata = r.json()

            chs = jdata.get('channels', [])
            for ch in chs:
                self.channels.append(PomoykaChannel(ch))
        except Exception as e:
            log.error(e)
        return self.channels

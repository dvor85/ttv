# -*- coding: utf-8 -*-

import os
import utils
import defines
import logger
from interface import Channel

log = logger.Logger('POMOYKA')


class PomoykaChannel(Channel):

    def get_id(self):
        return Channel.get_name(self)


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
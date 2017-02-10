# -*- coding: utf-8 -*-

import os
import utils
import defines
import logger

log = logger.Logger('POMOYKA')


class Pomoyka():

    def __init__(self):
        self.url = 'http://super-pomoyka.us.to/trash/ttv-list/ttv.json'
        self.channels = []

    def get_channels(self):
        try:
            r = defines.request(self.url)
            jdata = r.json()
            self.channels = jdata.get('channels', [])
        except Exception as e:
            log.error(e)
        return self.channels

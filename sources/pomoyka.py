# -*- coding: utf-8 -*-

import os
import utils
import defines
import logger
import xmltv
from interface import Channel

log = logger.Logger('POMOYKA')
fmt = utils.fmt


class PomoykaChannel(Channel):

    def get_id(self):
        return Channel.get_name(self)

    def get_logo(self):
        return utils.true_enc(
            fmt("{addon_path}/logo/{name}.png", addon_path=defines.ADDON_PATH, name=utils.true_enc(self.get_name(), 'utf8')))

    def get_epg(self):
        xmltv_epg = xmltv.XMLTV._instance
        if not self.data.get('epg') and xmltv_epg is not None:
            self.data['epg'] = []
            for ep in xmltv_epg.get_epg_by_name(self.get_name()):
                self.data['epg'].append(ep)

        return self.data.get('epg')


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

# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import utils
import defines
import logger
from tchannel import TChannel, TChannels
import xbmc
import os
import time
from channel_info import CHANNEL_INFO
try:
    import simplejson as json
except ImportError:
    import json

log = logger.Logger(__name__)
fmt = utils.fmt


class Channel(TChannel):

    def __init__(self, data={}):
        TChannel.__init__(self, data)
        self.data['players'] = ['internal']

    def get_url(self, player=None):
        if self.data.get('url'):
            r = defines.request(url=self.data.get('url'))
            urls = r.json()
            for u in urls:
                return u

    def get_group(self):
        name = utils.lower(self.get_name(), 'utf8')
        if not self.data.get('group'):
            try:
                self.data['group'] = CHANNEL_INFO[name]['cat']
            except KeyError:
                self.data['group'] = None
        for gr in self.data['group']:
            return gr

    def get_logo(self):
        name = utils.lower(self.get_name(), 'utf8')
        if not self.data.get('icon'):
            try:
                self.data['icon'] = CHANNEL_INFO[name]['logo']
            except KeyError:
                self.data['icon'] = ''

        logo = fmt("{addon_path}/resources/logo/{name}.png",
                   addon_path=utils.utf(defines.ADDON_PATH), name=utils.utf(self.get_name()))
        if os.path.exists(logo):
            self.data['icon'] = logo

        return self.data.get('icon')


class Channels(TChannels):

    def __init__(self):
        self.url = fmt('http://{pazl}:{port}/channels/json', pazl=defines.ADDON.getSetting('pazl_addr'),
                       port=defines.ADDON.getSetting('pazl_port'))
        TChannels.__init__(self, reload_interval=1800)

    def update_channels(self):
        TChannels.update_channels(self)
        try:
            jdata = self._load_jdata()
            if not jdata:
                raise Exception(fmt("{temp} is empty", temp=self._temp))

        except Exception as e:
            log.debug(fmt("load_json_temp error: {0}", e))
            try:
                r = defines.request(self.url)
                jdata = r.json()
            except Exception as e:
                log.error(fmt("get_channels error: {0}", e))

        chs = jdata.get('channels', [])
        for ch in chs:
            self.channels.append(Channel(ch))

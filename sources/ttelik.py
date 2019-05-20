# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import utils
import defines
import logger
from tchannel import TChannel, TChannels

log = logger.Logger(__name__)
fmt = utils.fmt


class Channel(TChannel):

    def get_id(self):
        return TChannel.get_name(self)


class Channels(TChannels):

    def __init__(self):
        self.url = fmt('http://{pomoyka}/trash/ttv-list/ttv.json', pomoyka=defines.ADDON.getSetting('pomoyka_domain'))
        TChannels.__init__(self, reload_interval=1800)

    def update_channels(self):
        TChannels.update_channels(self)
        try:
            r = defines.request(self.url)
            jdata = r.json()

            chs = jdata.get('channels', [])
            for ch in chs:
                self.channels.append(Channel(ch))
        except Exception as e:
            log.error(fmt("get_channels error: {0}", e))
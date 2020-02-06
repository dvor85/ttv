# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import defines
from . import allfon, acestream, ttv
from utils import str2int
from six.moves import UserList


class ChannelSources(UserList):
    def __init__(self, *args, **kwargs):
        UserList.__init__(self, *args, **kwargs)

    def index_by_name(self, src_name):
        for i, src in enumerate(self.data):
            if src.name == src_name:
                return i
        return -1

    def get_by_name(self, src_name):
        for src in self.data:
            if src.name == src_name:
                return src


channel_sources = ChannelSources()
if str2int(defines.ADDON.getSetting('allfon')) > 0:
    channel_sources.insert(str2int(defines.ADDON.getSetting('allfon')), allfon.Channels())
if str2int(defines.ADDON.getSetting('acestream')) > 0:
    channel_sources.insert(str2int(defines.ADDON.getSetting('acestream')), acestream.Channels())
if str2int(defines.ADDON.getSetting('ttv')) > 0:
    channel_sources.insert(str2int(defines.ADDON.getSetting('ttv')), ttv.Channels())

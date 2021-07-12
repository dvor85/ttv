# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import defines
from . import acestream, ttv, iptv_restream
from sources import acetv
from sources import playlists
from six.moves import UserList
from threading import Lock
from utils import str2int


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
_lock = Lock()
if str2int(defines.ADDON.getSetting('acetv')) > 0:
    channel_sources.append(acetv.Channels(_lock))
if str2int(defines.ADDON.getSetting('acestream')) > 0:
    channel_sources.append(acestream.Channels(_lock))
if str2int(defines.ADDON.getSetting('ttv')) > 0:
    channel_sources.append(ttv.Channels())
if str2int(defines.ADDON.getSetting('iptv')) > 0:
    channel_sources.append(iptv_restream.Channels(_lock))
if str2int(defines.ADDON.getSetting('playlists')) > 0:
    channel_sources.append(playlists.Channels())
channel_sources.sort(key=lambda src: str2int(defines.ADDON.getSetting(src.name)))

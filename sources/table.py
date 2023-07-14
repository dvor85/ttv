# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import defines
from . import acestream, ttv, iptv_restream
from sources import acetv
from sources import playlists
from sources import proxytv
from six.moves import UserList
from threading import Lock


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
if defines.ADDON.getSettingInt('acetv') > 0:
    channel_sources.append(acetv.Channels(_lock))
if defines.ADDON.getSettingInt('acestream') > 0:
    channel_sources.append(acestream.Channels(_lock))
if defines.ADDON.getSettingInt('ttv') > 0:
    channel_sources.append(ttv.Channels())
if defines.ADDON.getSettingInt('iptv-org.github.io') > 0:
    channel_sources.append(iptv_restream.Channels())
if defines.ADDON.getSettingInt('playlists') > 0:
    channel_sources.append(playlists.Channels())
if defines.ADDON.getSettingInt('proxytv') > 0:
    channel_sources.append(proxytv.Channels())

channel_sources.sort(key=lambda src: defines.ADDON.getSettingInt(src.name))

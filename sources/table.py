# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import defines
from . import allfon, acestream, ttv
from utils import str2int
from six import itervalues, iteritems, iterkeys, next
from six.moves import UserDict
from threading import Lock
from utils import str2int


class ChannelSources(UserDict):
    def __init__(self, *args, **kwargs):
        UserDict.__init__(self, *args, **kwargs)

    def index_by_name(self, src_name):
        for i, src in iteritems(self.data):
            if src.name == src_name:
                return str2int(i)
        return -1

    def get_by_name(self, src_name):
        for src in itervalues(self.data):
            if src.name == src_name:
                return src


channel_sources = ChannelSources()
_lock = Lock()
if str2int(defines.ADDON.getSetting('allfon')) > 0:
    channel_sources[defines.ADDON.getSetting('allfon')] = allfon.Channels(_lock)
if str2int(defines.ADDON.getSetting('acestream')) > 0:
    channel_sources[defines.ADDON.getSetting('acestream')] = acestream.Channels(_lock)
if str2int(defines.ADDON.getSetting('ttv')) > 0:
    channel_sources[defines.ADDON.getSetting('ttv')] = ttv.Channels()

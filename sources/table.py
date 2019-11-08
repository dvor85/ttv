# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import defines
from . import allfon, acestream
from utils import str2int

ChannelSources = {}
if str2int(defines.ADDON.getSetting('allfon')) > 0:
    ChannelSources['allfon'] = allfon.Channels(str2int(defines.ADDON.getSetting('allfon')))
if str2int(defines.ADDON.getSetting('acestream')) > 0:
    ChannelSources['acestream'] = acestream.Channels(str2int(defines.ADDON.getSetting('acestream')))

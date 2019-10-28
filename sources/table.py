# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

from . import allfon,  acestream
import defines

ChannelSources = {}
if defines.ADDON.getSetting('allfon') == 'true':
    ChannelSources['allfon'] = allfon.Channels()
if defines.ADDON.getSetting('acestream') == 'true':
    ChannelSources['acestream'] = acestream.Channels()

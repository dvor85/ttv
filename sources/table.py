# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru


import ttv
import ttelik
import allfon
import acestream
import defines

ChannelSources = {}
if defines.ADDON.getSetting('ttv') == 'true':
    ChannelSources['ttv'] = ttv.Channels()
if defines.ADDON.getSetting('ttelik') == 'true':
    ChannelSources['ttelik'] = ttelik.Channels()
if defines.ADDON.getSetting('allfon') == 'true':
    ChannelSources['allfon'] = allfon.Channels()
if defines.ADDON.getSetting('acestream') == 'true':
    ChannelSources['acestream'] = acestream.Channels()

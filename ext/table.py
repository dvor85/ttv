# -*- coding: utf-8 -*-

import tchannels
import onettvnet
import televizorhd
import aceliveChannels

Channels = {
            '1ttv.net': tchannels.TChannels(onettvnet.Channels), 
#             'televizorhd': tchannels.TChannels(televizorhd.Channels),
#             'aceliveChannels': tchannels.TChannels(aceliveChannels.Channels),
            }
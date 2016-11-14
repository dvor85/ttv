# -*- coding: utf-8 -*-

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

import tchannels
import onettvnet

Channels = OrderedDict((
    ('1ttv.net', tchannels.TChannels(onettvnet.Channels)),
    #             ('aceliveChannels', tchannels.TChannels(aceliveChannels.Channels)),
    #             ('televizorhd', tchannels.TChannels(televizorhd.Channels)),
))

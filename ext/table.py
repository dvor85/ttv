# -*- coding: utf-8 -*-

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

import tchannels
import onettvnet
import pomoyka

Channels = OrderedDict((
    #     ('1ttv.net', tchannels.TChannels(onettvnet.Channels)),
    ('Pomoyka', tchannels.TChannels(pomoyka.Pomoyka().get_channels())),
    #             ('aceliveChannels', tchannels.TChannels(aceliveChannels.Channels)),
    #             ('televizorhd', tchannels.TChannels(televizorhd.Channels)),
))

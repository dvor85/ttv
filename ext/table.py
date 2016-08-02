# -*- coding: utf-8 -*-
from collections import OrderedDict

import tchannels
import onettvnet
import televizorhd
import aceliveChannels

Channels = OrderedDict((
            ('1ttv.net', tchannels.TChannels(onettvnet.Channels)), 
#             ('aceliveChannels', tchannels.TChannels(aceliveChannels.Channels)),
#             ('televizorhd', tchannels.TChannels(televizorhd.Channels)),
            ))
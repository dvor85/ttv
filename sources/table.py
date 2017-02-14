# -*- coding: utf-8 -*-

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

import ttv
import pomoyka

Channels = OrderedDict((
    ('ttv', ttv.TTV()),
    ('pomoyka', pomoyka.Pomoyka()),
))

# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals

import defines
import logger

log = logger.Logger('STARTUP')


if defines.AUTOSTART:
    import xbmc

    xbmc.executebuiltin('RunAddon({0})'.format(defines.ADDON_ID))

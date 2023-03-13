# -*- coding: utf-8 -*-

import defines
import logger

log = logger.Logger('STARTUP')

if defines.AUTOSTART:
    import xbmc

    xbmc.executebuiltin('RunAddon({0})'.format(defines.ADDON_ID))

# -*- coding: utf-8 -*-
import defines
import logger
import os
from xml.etree.ElementTree import ElementTree

log = logger.Logger('STARTUP')
log("{0} v.{1}".format(defines.ADDON_ID, defines.ADDON.getAddonInfo('version')))

dom = ElementTree()
dom.parse(defines.ADDON_PATH + '/resources/settings.xml')
xset = None
for sett in dom.find('category').findall('setting'):
    if sett.attrib['id'] == 'skin':
        xset = sett
        break

if os.path.exists(defines.DATA_PATH + '/resources/skins/'):
    dirs = os.listdir(defines.DATA_PATH + '/resources/skins/')
    val = "st.anger|" + "|".join(dirs)
    if xset.attrib['values'] != val:
        xset.attrib['values'] = val
        dom.write(defines.ADDON_PATH + '/resources/settings.xml', 'utf-8')
elif xset.attrib['values'] != "st.anger":
    xset.attrib['values'] = "st.anger"
    dom.write(defines.ADDON_PATH + '/resources/settings.xml', 'utf-8')

if defines.AUTOSTART:
    import xbmc
    xbmc.executebuiltin('RunAddon({0})'.format(defines.ADDON_ID))

# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals

import os

import defines
import logger

log = logger.Logger('STARTUP')


def add_skins():
    try:

        try:
            # Python 2.5
            import xml.etree.cElementTree as etree
        except ImportError:
            # Python 2.5
            import xml.etree.ElementTree as etree

        log("{0} v.{1}".format(defines.ADDON_ID, defines.ADDON.getAddonInfo('version')))

        set_file = os.path.join(defines.ADDON_PATH, 'resources/settings.xml')
        skins_dir = os.path.join(defines.DATA_PATH + 'resources/skins/')

        root = etree.parse(set_file)
        xset = None
        for sett in root.find('category').findall('setting'):
            if sett.attrib['id'] == 'skin':
                xset = sett
                break

        if os.path.exists(skins_dir):
            val = "st.anger|" + "|".join(os.listdir(skins_dir))
            if xset.attrib['values'] != val:
                xset.attrib['values'] = val
                root.write(set_file, 'utf-8')
        elif xset.attrib['values'] != "st.anger":
            xset.attrib['values'] = "st.anger"
            root.write(set_file, 'utf-8')

    except Exception as e:
        log.e('add_skins error: {0}'.format(e))

add_skins()

if defines.AUTOSTART:
    import xbmc

    xbmc.executebuiltin('RunAddon({0})'.format(defines.ADDON_ID))

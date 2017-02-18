# -*- coding: utf-8 -*-
# Copyright (c) 2013 Torrent-TV.RU
# Writer (c) 2011, Welicobratov K.A., E-mail: 07pov23@gmail.com
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import defines
import xmltv


try:
    if defines.DEBUG:
        import debug  # @UnusedImport
except Exception as e:
    defines.log(e)


def checkPort(*args):
    param = args[0]
    if not defines.checkPort(param):
        mess = "Порт %s закрыт. \
        Для стабильной работы сервиса и трансляций, настоятельно рекомендуется его открыть." % defines.ADDON.getSetting('outport')
        defines.showNotification(mess)
        defines.log(mess)


def main():
    import mainform
    if not defines.ADDON.getSetting('skin'):
        defines.ADDON.setSetting('skin', 'st.anger')
    if defines.ADDON.getSetting("skin") == "default":
        defines.ADDON.setSetting("skin", "st.anger")
    if not defines.ADDON.getSetting("login"):
        defines.ADDON.setSetting("login", "anonymous")
        defines.ADDON.setSetting("password", "anonymous")
    defines.MyThread(xmltv.XMLTV.get_instance).start()

    w = mainform.WMainForm("mainform.xml", defines.SKIN_PATH, defines.ADDON.getSetting('skin'))
    w.doModal()
    defines.log('Close plugin')
#     defines.showNotification('Close plugin')
    del w


if __name__ == '__main__':
    main()

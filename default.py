# -*- coding: utf-8 -*-
# Copyright (c) 2013 Torrent-TV.RU
# Writer (c) 2011, Welicobratov K.A., E-mail: 07pov23@gmail.com
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import defines
# try:
if defines.DEBUG:
    import debug  # @UnusedImport
# except Exception as e:
#     defines.log.error(e)
import mainform
from proxyserver import MyProxyServer


def main():

    w = mainform.WMainForm("mainform.xml", defines.ADDON_PATH)
    try:
        proxy_server = MyProxyServer(*defines.PROXY_ADDR_PORT)
        defines.MyThread(proxy_server.serve_forever).start()
        w.doModal()
    finally:
        defines.log('Close plugin')
        proxy_server.shutdown()
        del w


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
# Copyright (c) 2013 Torrent-TV.RU
# Writer (c) 2011, Welicobratov K.A., E-mail: 07pov23@gmail.com
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals
import defines


try:
    if defines.DEBUG:
        import debug  # @UnusedImport
except Exception as e:
    defines.log.error(e)


def main():
    import mainform

    w = mainform.WMainForm("mainform.xml", defines.SKIN_PATH, "st.anger")
    w.doModal()
    defines.log('Close plugin')
    del w


if __name__ == '__main__':
    main()

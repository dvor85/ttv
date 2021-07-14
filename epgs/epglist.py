# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals
import defines
from utils import uni
from . import mailtv, xmltv


class Epg():
    def __init__(self):
        self.source = uni(defines.ADDON.getSetting('epg_source'))

    @property
    def link(self):
        if self.source == "mailtv":
            return mailtv.MAILTV.get_instance()
        else:
            return xmltv.XMLTV.get_instance()

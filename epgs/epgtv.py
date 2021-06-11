# -*- coding: utf-8 -*-
# Writer (c) 2021, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import datetime
import os
import re
import time
from threading import Event
import defines
import logger
from utils import uni, str2int, fs_str, makedirs


log = logger.Logger(__name__)
_name_offset_regexp = re.compile(r'\s*(?P<name>.*?)\s*\((?P<offset>[\-+]+\d)\)\s*')


def strptime(date_string, _format="%Y-%m-%dT%H:%M:%S"):
    try:
        return datetime.datetime.strptime(uni(date_string), _format)
    except TypeError:
        return datetime.datetime(*(time.strptime(uni(date_string), _format)[0:6]))


def get_name_offset(name):
    name_offset = _name_offset_regexp.search(name)
    if name_offset:
        return name_offset.group('name'), str2int(name_offset.group('offset'))
    else:
        return name, None


class EPGTV:
    _instance = None
    _lock = Event()

    @staticmethod
    def get_instance():
        if EPGTV._instance is None:
            if not EPGTV._lock.is_set():
                EPGTV._lock.set()
                try:
                    EPGTV._instance = EPGTV()
                except Exception as e:
                    log.error("get_instance error: {0}".format(e))
                    EPGTV._instance = None
                finally:
                    EPGTV._lock.clear()
        return EPGTV._instance

    def __init__(self, name):
        log.d('start initialization')
        self.jdata = {}
        self.update_timer = None
        self.epgtv_path = os.path.join(defines.CACHE_PATH, name)
        self.epgtv_logo_path = os.path.join(defines.CACHE_PATH, 'logo')
        makedirs(fs_str(self.epgtv_path))
        self.limit_channels = 24

    def update_epg(self, page=0):
        pass

    def get_epg_by_id(self, chid, epg_offset=None):
        pass

    def get_id_by_name(self, name):
        pass

    def get_event_info(self, event_id):
        pass

    def get_epg_by_name(self, name):
        name_offset = get_name_offset(name)
        return self.get_epg_by_id(self.get_id_by_name(name_offset[0]), name_offset[1])

    def get_logo_by_id(self, chid):
        return ''

    def get_logo_by_name(self, name):
        name_offset = get_name_offset(name)
        return self.get_logo_by_id(self.get_id_by_name(name_offset[0]))


if __name__ == '__main__':
    pass

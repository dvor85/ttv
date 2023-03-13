# -*- coding: utf-8 -*-
# Writer (c) 2021, Vorotilin D.V., E-mail: dvor85@mail.ru

import datetime
import re
import time
from threading import Event
import defines
import logger
from pathlib import Path
from utils import str2int

log = logger.Logger(__name__)
_name_offset_regexp = re.compile(r'\s*(?P<name>.*?)\s*\(+(?P<offset>[\-+]+\d)\)+\s*')


def strptime(date_string, _format="%Y-%m-%dT%H:%M:%S"):
    try:
        return datetime.datetime.strptime(date_string, _format)
    except TypeError:
        return datetime.datetime(*(time.strptime(date_string, _format)[0:6]))


def get_name_offset(name):
    name_offset = _name_offset_regexp.search(name)
    if name_offset:
        return name_offset.group('name'), str2int(name_offset.group('offset'))
    else:
        return name, None


class EPGTV:
    _instance = None
    _lock = Event()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            if not cls._lock.is_set():
                cls._lock.set()
                try:
                    cls._instance = cls()
                except Exception as e:
                    log.error(f"get_instance error: {e}")
                    cls._instance = None
                finally:
                    cls._lock.clear()
        return cls._instance

    def __init__(self, name):
        log.d('start initialization')
        self.epgtv_path = Path(defines.CACHE_PATH, name)
        self.epgtv_logo_path = Path(defines.CACHE_PATH, 'logo')
        self.epgtv_path.mkdir(parents=True, exist_ok=True)

    def update_epg(self, page=0):
        raise NotImplementedError

    def get_epg_by_id(self, chid, epg_offset=None):
        raise NotImplementedError

    def get_id_by_name(self, name):
        raise NotImplementedError

    def get_event_info(self, event_id):
        raise NotImplementedError

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

# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
import datetime
import time
import utils
import defines
import logger
from threading import Event
import weakref

import os
import gzip


fmt = utils.fmt
log = logger.Logger(__name__)


class XMLTV():
    _instance = None
    _lock = Event()

    @staticmethod
    def get_instance():
        if XMLTV._instance is None:
            if not XMLTV._lock.is_set():
                XMLTV._lock.set()
                try:
                    XMLTV._instance = XMLTV()
                finally:
                    XMLTV._lock.clear()
        return XMLTV._instance

    def __init__(self):
        try:
            log.d('start initialization')
            self.xmltv_file = os.path.join(defines.DATA_PATH, 'ttv.xmltv.xml.gz')
            if os.path.exists(self.xmltv_file):
                dt = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(self.xmltv_file))

            if not os.path.exists(self.xmltv_file) or dt.days >= 1:
                self.update_xmltv()
            with gzip.open(self.xmltv_file, 'rb') as fp:
                self.xmltv_root = weakref.ref(ET.XML(fp.read()))
            log.d('stop initialization')
        except Exception as e:
            log.error(fmt("XMLTV not initialazed. {0}", e))

    def update_xmltv(self):
        url = 'http://api.torrent-tv.ru/ttv.xmltv.xml.gz'
        r = defines.request(url)
        with open(self.xmltv_file, 'wb') as fp:
            fp.write(r.content)

    def get_channels(self):
        for chid in self.xmltv_root().iter('channel'):
            for name in chid.iter('display-name'):
                yield {'id': chid.get('id'), 'name': name.text}

    def strptime(self, date_string):
        try:
            return datetime.datetime.strptime(date_string, "%Y%m%d%H%M%S")
        except TypeError:
            return datetime.datetime(*(time.strptime(date_string, "%Y%m%d%H%M%S")[0:6]))

    def get_epg_by_id(self, chid):
        if chid is None:
            return
        ctime = datetime.datetime.now()
        offset = int(round((ctime - datetime.datetime.utcnow()).total_seconds()) / 3600)
        for programme in self.xmltv_root().iter('programme'):
            if programme.get('channel') == chid:
                ep = {}

                bt = programme.get('start').split()
                bt = self.strptime(bt[0]) + datetime.timedelta(hours=-3 + offset)
                ep['btime'] = time.mktime(bt.timetuple())

                et = programme.get('stop').split()
                et = self.strptime(et[0]) + datetime.timedelta(hours=-3 + offset)
                ep['etime'] = time.mktime(et.timetuple())

                ep['name'] = programme.iter('title').next().text

                yield ep

    def get_id_by_name(self, name):
        name = utils.utf(name).lower()
        for ch in self.get_channels():
            if utils.utf(ch['name']).lower() == name:
                return ch['id']

    def get_epg_by_name(self, name):
        return self.get_epg_by_id(self.get_id_by_name(name))


if __name__ == '__main__':
    pass

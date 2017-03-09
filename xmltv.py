# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import xml.etree.cElementTree as ET
import datetime
import time
import utils
import defines
import logger
from threading import Event

import os
import gzip


fmt = utils.fmt
log = logger.Logger(__name__)
_servers = ['api.torrent-tv.ru', '1ttvxbmc.top']


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
        self.channels = {}
        self.xmltv_root = None
        try:
            log.d('start initialization')
            self.xmltv_file = os.path.join(defines.DATA_PATH, 'xmltv.xml.gz')
            same_date = False
            if os.path.exists(self.xmltv_file):
                same_date = datetime.date.today() == datetime.date.fromtimestamp(os.path.getmtime(self.xmltv_file))

            if not os.path.exists(self.xmltv_file) or not same_date:
                self.update_xmltv()
            # при многократном запуске плагина возникает утечка памяти. Решение: weakref, но возникает ошибка создания ссылки
            with gzip.open(self.xmltv_file, 'rb') as fp:
                self.xmltv_root = ET.XML(fp.read())

            log.d('stop initialization')
        except Exception as e:
            log.error(fmt("XMLTV not initialazed. {0}", e))
            XMLTV._instance = None

    def update_xmltv(self):
        for server in _servers:
            try:
                #    url = 'http://www.teleguide.info/download/new3/xmltv.xml.gz'
                url = fmt('http://{server}/ttv.xmltv.xml.gz', server=server)
                r = defines.request(url)
                with open(self.xmltv_file, 'wb') as fp:
                    fp.write(r.content)
                return True
            except Exception as e:
                log.error(fmt('update_xmltv error: {0}', e))

    def get_channels(self):
        if not self.channels:
            for chid in self.xmltv_root.iter('channel'):
                for name in chid.iter('display-name'):
                    self.channels[chid.get('id')] = {'name': name.text}
        return self.channels

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
        for programme in self.xmltv_root.iter('programme'):
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
        name = utils.lower(name, 'utf8')
        for chid, ch in self.get_channels().iteritems():
            if utils.lower(ch['name'], 'utf8') == name:
                return chid

    def get_epg_by_name(self, name):
        return self.get_epg_by_id(self.get_id_by_name(name))


if __name__ == '__main__':
    pass

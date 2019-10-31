# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import datetime
import gzip
import os
import time
from threading import Event
from six import iteritems
import defines
import logger
import utils
from utils import uni, str2

log = logger.Logger(__name__)


def strptime(date_string):
    try:
        return datetime.datetime.strptime(uni(date_string), "%Y-%m-%dT%H:%M:%S")
    except TypeError:
        return datetime.datetime(*(time.strptime(uni(date_string), "%Y-%m-%dT%H:%M:%S")[0:6]))


class XMLTV:
    _instance = None
    _lock = Event()
    _xml_lib = 0

    @staticmethod
    def get_instance():
        if XMLTV._instance is None:
            if not XMLTV._lock.is_set():
                XMLTV._lock.set()
                try:
                    XMLTV._instance = XMLTV()
                except Exception as e:
                    log.error("get_instance error: {0}".format(e))
                    XMLTV._instance = None
                finally:
                    XMLTV._lock.clear()
        return XMLTV._instance

    def __init__(self):
        self.yatv()
        try:
            from lxml import etree
            XMLTV._xml_lib = 0
            log.d("running with lxml.etree")
        except ImportError:
            try:
                # Python 2.5
                if XMLTV._xml_lib > 0:
                    raise Exception("Already try this library")
                import xml.etree.cElementTree as etree
                XMLTV._xml_lib = 1
                log.d("running with cElementTree")
            except Exception:
                # Python 2.5
                import xml.etree.ElementTree as etree
                XMLTV._xml_lib = 2
                log.d("running with ElementTree")

        self.channels = {}
        self.xmltv_root = None
        log.d('start initialization')
        self.epg_url = uni(defines.ADDON.getSetting('epg_url'))
        self.xmltv_file = os.path.join(defines.CACHE_PATH, 'xmltv.xml.gz')
        self.xmltv_file_json = os.path.join(defines.CACHE_PATH, 'xmltv.dump.gz')

        same_date = False
        if os.path.exists(self.xmltv_file):
            same_date = datetime.date.today() == datetime.date.fromtimestamp(os.path.getmtime(self.xmltv_file))

        if not os.path.exists(self.xmltv_file) or not same_date:
            self.update_xmltv()
            if os.path.exists(self.xmltv_file_json):
                os.unlink(self.xmltv_file_json)

        """
        при многократном запуске плагина возможно возникновение утечки памяти.
        Решение: weakref, но возникает ошибка создания ссылки
        """
        with gzip.open(self.xmltv_file, 'rb') as fp:
            bt = time.time()
            self.xmltv_root = etree.parse(fp)
            log.d("Parse xmltv in {t} sec".format(t=time.time() - bt))

        log.d('stop initialization')

    def update_xmltv(self):
        try:
            #url = 'http://www.teleguide.info/download/new3/xmltv.xml.gz'
            url = self.epg_url
            r = defines.request(url)
            with open(self.xmltv_file, 'wb') as fp:
                fp.write(r.content)
            return True
        except Exception as e:
            log.error('update_xmltv error: {0}'.format(e))

    def get_channels(self):
        if not self.channels:
            for chid in self.xmltv_root.iter('channel'):
                for name in chid.iter('display-name'):
                    self.channels[chid.get('id')] = {'name': name.text}
        return self.channels

    def get_epg_by_id(self, chid, epg_offset=None):
        if chid is None:
            return
        ctime = datetime.datetime.now()
        offset = (ctime - datetime.datetime.utcnow()).total_seconds() // 3600 if epg_offset is None else epg_offset
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
        for chid, ch in iteritems(self.get_channels()):
            if ch['name'].lower() == name.lower():
                return chid

    def get_epg_by_name(self, name):
        return self.get_epg_by_id(self.get_id_by_name(name))


if __name__ == '__main__':
    pass

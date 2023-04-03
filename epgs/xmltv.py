# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import datetime
import gzip
import time
from threading import Event
import defines
import logger
from pathlib import Path
from sources.channel_info import ChannelInfo
from epgs.epgtv import EPGTV, strptime

log = logger.Logger(__name__)


class XMLTV(EPGTV):
    _instance = None
    _lock = Event()
    _xml_lib = 0

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

    def __init__(self):
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
        EPGTV.__init__(self, 'xmltv')

        self.channels = {}
        self.xmltv_root = None
        self.xmltv_file = Path(self.epgtv_path, "xmltv.xml.gz")
        self.epg_url = defines.ADDON.getSetting('epg_url')
        self.chinfo = ChannelInfo().get_instance()

        valid_date = self.xmltv_file.exists() and datetime.date.today() == datetime.date.fromtimestamp(self.xmltv_file.stat().st_mtime)

        if not valid_date:
            self.update_epg()

        """
        при многократном запуске плагина возможно возникновение утечки памяти.
        Решение: weakref, но возникает ошибка создания ссылки
        """
        with gzip.open(self.xmltv_file, 'r') as fp:
            bt = time.time()
            self.xmltv_root = etree.parse(fp)
            log.d(f"Parse xmltv in {time.time() - bt} sec")

        log.d('stop initialization')

    def update_epg(self):
        try:
            # url = 'http://www.teleguide.info/download/new3/xmltv.xml.gz'
            url = self.epg_url
            r = defines.request(url)
            with gzip.open(self.xmltv_file, 'w') as fp:
                fp.write(r.content)
            return True
        except Exception as e:
            log.error(f'update_xmltv error: {e}')

    def get_channels(self):
        if not self.channels:
            [[self.channels.setdefault(chid.get('id'), {'name': name.text}) for name in chid.iter('display-name')] for chid in self.xmltv_root.iter('channel')]

        return self.channels

    def get_epg_by_id(self, chid, epg_offset=None):
        if chid is None:
            return
        ctime = datetime.datetime.now()
        offset = round((ctime - datetime.datetime.utcnow()).total_seconds() / 3600) - 3
        if epg_offset is not None:
            offset -= epg_offset
        for programme in self.xmltv_root.iter('programme'):
            if programme.get('channel') == chid:
                ep = {}

                bt = programme.get('start').split()
                bt = strptime(bt[0], "%Y%m%d%H%M%S") + datetime.timedelta(hours=offset)
                ep['btime'] = time.mktime(bt.timetuple())

                et = programme.get('stop').split()
                et = strptime(et[0], "%Y%m%d%H%M%S") + datetime.timedelta(hours=offset)
                ep['etime'] = time.mktime(et.timetuple())

                ep['name'] = programme.iter('title').next().text

                yield ep

    def get_id_by_name(self, name):
        name = name.lower()
        name_wo_hd = name.replace(' hd', '') if name.endswith(' hd') else name
        names = {name, name.replace('-', ' '), name_wo_hd}
        for n in names.copy():
            chinfo = self.chinfo.get_channel_by_name(n)
            if chinfo:
                if chinfo.get('ch_epg'):
                    names = {chinfo['ch_epg']}
                elif chinfo.get('ch_title'):
                    names.add(chinfo['ch_title'])
                break

        return next((chid for chid, ch in self.get_channels().items() if ch['name'].lower() in names), None)


if __name__ == '__main__':
    pass

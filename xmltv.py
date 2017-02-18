# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
import datetime
import time
import utils
import defines
import logger

import os
import gzip


fmt = utils.fmt
log = logger.Logger('XMLTV')


class XMLTV():
    _instance = None

    @staticmethod
    def get_instance():
        if XMLTV._instance is None:
            XMLTV._instance = XMLTV()
        return XMLTV._instance

    def __init__(self):
        self.xmltv_file = os.path.join(defines.DATA_PATH, 'ttv.xmltv.xml.gz')
        if os.path.exists(self.xmltv_file):
            dt = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(self.xmltv_file))

        if not os.path.exists(self.xmltv_file) or dt.days > 2:
            self.update_xmltv()
        with gzip.open(self.xmltv_file, 'rb') as fp:
            self.xmltv_root = ET.XML(fp.read())

    def update_xmltv(self):
        url = 'http://api.torrent-tv.ru/ttv.xmltv.xml.gz'
        r = defines.request(url)
        with open(self.xmltv_file, 'wb') as fp:
            fp.write(r.content)

    def get_channels(self):
        for chid in self.xmltv_root.iter('channel'):
            for name in chid.iter('display-name'):
                yield {'id': chid.get('id'), 'name': name.text}

    def get_epg_by_id(self, chid):
        if chid is None:
            return
        ctime = datetime.datetime.now()
        prev_bt = 0
        prev_et = 0
        offset = int(round((datetime.datetime.now() - datetime.datetime.utcnow()).total_seconds()) / 3600)
        for programme in self.xmltv_root.iter('programme'):
            if programme.get('channel') == chid:
                ep = {}

                bt = programme.get('start').split()
                bt = datetime.datetime.strptime(bt[0], "%Y%m%d%H%M%S") + datetime.timedelta(hours=-3 + offset)
                ep['btime'] = time.mktime(bt.timetuple())

                et = programme.get('stop').split()
                et = datetime.datetime.strptime(et[0], "%Y%m%d%H%M%S") + datetime.timedelta(hours=-3 + offset)
                ep['etime'] = time.mktime(et.timetuple())

                ep['name'] = programme.iter('title').next().text

                if et > ctime and abs((bt.date() - ctime.date()).days) <= 1 and prev_et <= float(ep['btime']) > prev_bt:
                    yield ep
                    prev_bt = float(ep['btime'])
                    prev_et = float(ep['etime'])

    def get_id_by_name(self, name):
        name = utils.utf(name)
        for ch in self.get_channels():
            if utils.utf(ch['name']).lower() == name.lower():
                return ch['id']

    def get_epg_by_name(self, name):
        return self.get_epg_by_id(self.get_id_by_name(name))


if __name__ == '__main__':
    pass

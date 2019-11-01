# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import datetime
import gzip
import json
import os
import re
import time
from threading import Event, Timer
import requests
import defines
import logger
from sources.channel_info import CHANNEL_INFO
from utils import uni, str2, str2int


log = logger.Logger(__name__)
_name_offset_regexp = re.compile(r'\s*(?P<name>.*?)\s*\((?P<offset>[\-+]+\d)\)\s*')


def strptime(date_string):
    try:
        return datetime.datetime.strptime(uni(date_string), "%Y-%m-%dT%H:%M:%S")
    except TypeError:
        return datetime.datetime(*(time.strptime(uni(date_string), "%Y-%m-%dT%H:%M:%S")[0:6]))


def get_name_offset(name):
    name_offset = _name_offset_regexp.search(name)
    if name_offset:
        return name_offset.group('name'), str2int(name_offset.group('offset'))


class YATV:
    _instance = None
    _lock = Event()

    @staticmethod
    def get_instance():
        if YATV._instance is None:
            if not YATV._lock.is_set():
                YATV._lock.set()
                try:
                    YATV._instance = YATV()
                except Exception as e:
                    log.error("get_instance error: {0}".format(e))
                    YATV._instance = None
                finally:
                    YATV._lock.clear()
        return YATV._instance

    def __init__(self):
        log.d('start initialization')
        self.jdata = []
        self.update_timer = None
        self.yatv_file_json = os.path.join(defines.CACHE_PATH, 'yatv.json.gz')
        self.yatv_logo_path = os.path.join(defines.CACHE_PATH, 'logo')
        self.sess = requests.Session()

        self.availableChannels = self.get_availible_channels()
        self._get_jdata()

        log.d('stop initialization')

    def _get_jdata(self):
        valid_date = False
        if os.path.exists(self.yatv_file_json):
            valid_date = datetime.date.today() == datetime.date.fromtimestamp(os.path.getmtime(self.yatv_file_json))
        interval = (datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=1),
                                              datetime.time(3, 0)) - datetime.datetime.now()).seconds

        if not os.path.exists(self.yatv_file_json) or not valid_date:
            if os.path.exists(self.yatv_file_json):
                os.unlink(self.yatv_file_json)
            bt = time.time()
            self.update_yatv()
            log.d("Loading yatv in {t} sec".format(t=time.time() - bt))
        if not self.jdata:
            try:
                bt = time.time()
                with gzip.open(self.yatv_file_json, 'rb') as fp:
                    self.jdata = json.load(fp)
                log.d("Loading yatv from json in {t} sec".format(t=time.time() - bt))
            except Exception as e:
                log.e("Error while loading json: {0}".format(uni(e)))
                if os.path.exists(self.yatv_file_json):
                    os.unlink(self.yatv_file_json)
                raise e

        self.update_timer = Timer(interval, self._get_jdata)
        self.update_timer.name = "update_yatv_timer"
        self.update_timer.daemon = False
        self.update_timer.start()

    def cancel(self):
        if self.update_timer:
            self.update_timer.cancel()
            self.update_timer = None

    def get_yatv_sess(self):
        return self.sess

    def get_availible_channels(self):
        ncrd = uni(int(time.time()) * 1000 + 1080)
        url = 'https://m.tv.yandex.ru/ajax/i-tv-region/get'
        _yparams = {"fields": "availableChannels,availableChannelsIds"}
        _params = {"userRegion": 193,
                   "resource": "schedule",
                   "ncrd": ncrd,
                   "params": json.dumps(_yparams),
                   "lang": "ru"
                   }
        r = defines.request(url, params=_params, session=self.sess, headers={'Referer': 'https://tv.yandex.ru/'})
        return r.json()

    def update_yatv(self):
        ncrd = uni(int(time.time()) * 1000 + 1080)
        dtm = uni(time.strftime('%Y-%m-%d'))

        url = 'https://m.tv.yandex.ru/ajax/i-tv-region/get'
        """
        https://tv.yandex.ru/ajax/i-tv-region/get?params={"duration":96400,"fields":"schedules,channel,title,id,events,channelId,start,finish,program,availableChannels,availableChannelsIds"}&resource=schedule&lang=ru&userRegion=193
        """

        _yparams = {"fields": "schedules,channel,title,id,events,description,channelId,start,finish,program,logo,sizes,src,images",
                    "channelLimit": 24,
                    "channelProgramsLimit": self.availableChannels["availableChannels"],
                    "channelOffset": 0,
                    "start": dtm + 'T03:00:00+03:00'
                    }
        _params = {"userRegion": 193,
                   "resource": "schedule",
                   "ncrd": ncrd,
                   "params": json.dumps(_yparams),
                   "lang": "ru"
                   }
        with gzip.open(self.yatv_file_json, 'ab+') as fp:
            fp.write('[')
            m = int(round(_yparams["channelProgramsLimit"] / _yparams["channelLimit"]))
            for p in range(0, m):
                _yparams["channelOffset"] = p * _yparams["channelLimit"]
                _params["params"] = json.dumps(_yparams)

                #                 url = 'https://m.tv.yandex.ru/ajax/i-tv-region/get?params=%7B"channelLimit"%3A' + str(limit) + '%2C"channelOffset"%3A' + \
                #                     str(n * limit) + \
                #                     '%2C"fields"%3A"channel%2Ctitle%2Cid%2Clogo%2Csizes%2Cwidth%2Cheight%2Csrc%2Ccopyright%2Cschedules%2Cchannels%2CavailableProgramTypes%2Celement%2Cid%2Cname%2Cevents%2Cid%2CchannelId%2Cepisode%2Cdescription%2CseasonName%2CseasonNumber%2Cid%2CprogramId%2Cstart%2Cfinish%2Cprogram%2Cid%2Ctype%2Cid%2Cname"%2Cstart"%3A"' + dtm + \
                #                     'T03%3A00%3A00%2B03%3A00"%2C"duration"%3A96400%2C"channelProgramsLimit"%3A500%2C"lang"%3A"ru"%7D&userRegion=193&resource=schedule&ncrd=' + ncrd
                try:
                    r = defines.request(url, params=_params, session=self.sess, headers={'Referer': 'https://tv.yandex.ru/'})
                    fp.write(r.content)
                    if p < m - 1:
                        fp.write(',')
                except Exception as e:
                    log.error('update_yatv error: {0}'.format(e))
            fp.write(']')

    def get_finish(self):
        m = None
        for p in self.jdata:
            for sch in p['schedules']:
                try:
                    cm = strptime(sch['finish'].split('+')[0])
                    if not m or m > cm:
                        m = cm
                except Exception as e:
                    pass
        if not m:
            return datetime.datetime.now()
        return m

    def get_epg_by_id(self, chid, epg_offset=None):
        if chid is None or chid not in self.availableChannels["availableChannelsIds"]:
            return
        ctime = datetime.datetime.now()
        offset = (ctime - datetime.datetime.utcnow()).total_seconds() // 3600 if epg_offset is None else epg_offset
        for p in self.jdata:
            for sch in p['schedules']:
                if sch['channel']['id'] == chid:
                    for evt in sch['events']:
                        ep = {}
                        bt = evt['start'].split('+')
                        bt = strptime(bt[0]) + datetime.timedelta(hours=-3 + offset)
#                         bt = self.strptime(bt[0])
                        ep['btime'] = time.mktime(bt.timetuple())
                        et = evt['finish'].split('+')
                        et = strptime(et[0]) + datetime.timedelta(hours=-3 + offset)
#                         et = self.strptime(et[0])
                        ep['etime'] = time.mktime(et.timetuple())
                        ep['name'] = evt['program']['title']
                        ep['desc'] = evt['program'].get('description', '')
                        if 'images' in evt['program']:
                            ep['screens'] = ['http:{src}'.format(src=x['sizes']['200']['src']) for x in evt['program']['images']]

                        yield ep

    def get_id_by_name(self, name):
        names = [name.lower()]
        names.extend(CHANNEL_INFO.get(names[0], {}).get("aliases", []))
        for p in self.jdata:
            for sch in p['schedules']:
                if sch['channel']['title'].lower() in names:
                    return sch['channel']['id']

    def get_epg_by_name(self, name):
        name_offset = get_name_offset(name)
        if name_offset:
            return self.get_epg_by_id(self.get_id_by_name(name_offset[0]), name_offset[1])
        else:
            return self.get_epg_by_id(self.get_id_by_name(name))

    def get_logo_by_id(self, chid):
        if chid is None or chid not in self.availableChannels["availableChannelsIds"]:
            return ''
        for p in self.jdata:
            for sch in p['schedules']:
                if sch['channel']['id'] == chid:
                    if 'logo' in sch['channel']:
                        return 'http:{src}'.format(src=sch['channel']['logo']['sizes']["160"]["src"])
        return ''

    def get_logo_by_name(self, name):
        name_offset = get_name_offset(name)
        if name_offset:
            return self.get_logo_by_id(self.get_id_by_name(name_offset[0]))
        else:
            return self.get_logo_by_id(self.get_id_by_name(name))


if __name__ == '__main__':
    pass

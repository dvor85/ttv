# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import datetime
import time
import utils
import defines
import logger
import requests
from threading import Event

import os
try:
    import simplejson as json
except ImportError:
    import json

fmt = utils.fmt
log = logger.Logger(__name__)


class YATV():
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
                    log.error(fmt("get_instance error: {0}", e))
                    YATV._instance = None
                finally:
                    YATV._lock.clear()
        return YATV._instance

    def __init__(self):
        log.d('start initialization')
        self.jdata = []
        self.yatv_file_json = os.path.join(defines.CACHE_PATH, 'yatv.json')
        self.yatv_logo_path = os.path.join(defines.CACHE_PATH, 'logo')
        self.sess = requests.Session()

        valid_date = False
        if os.path.exists(self.yatv_file_json):
            valid_date = datetime.date.today() == datetime.date.fromtimestamp(os.path.getmtime(self.yatv_file_json))

        self.availableChannels = self.get_availible_channels()

        if not os.path.exists(self.yatv_file_json) or not valid_date:
            if os.path.exists(self.yatv_file_json):
                os.unlink(self.yatv_file_json)
            bt = time.time()
            self.update_yatv()
            log.d(fmt("Loading yatv in {t} sec", t=time.time() - bt))
        if not self.jdata:
            bt = time.time()
            with open(self.yatv_file_json, 'rb') as fp:
                self.jdata = json.load(fp)
            log.d(fmt("Loading yatv from json in {t} sec", t=time.time() - bt))
#         if self.jdata:
#             ft = time.mktime(self.get_finish().timetuple())
#             os.utime(self.yatv_file_json, (ft, ft))
        log.d('stop initialization')

    def get_yatv_sess(self):
        return self.sess

    def get_availible_channels(self):
        ncrd = str(long(time.time()) * 1000 + 1080)
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
        ncrd = str(long(time.time()) * 1000 + 1080)
        dtm = time.strftime('%Y-%m-%d')

        url = 'https://m.tv.yandex.ru/ajax/i-tv-region/get'
        """
        https://tv.yandex.ru/ajax/i-tv-region/get?params={"duration":96400,"fields":"schedules,channel,title,id,events,channelId,start,finish,program,availableChannels,availableChannelsIds"}&resource=schedule&lang=ru&userRegion=193
        """

        _yparams = {"fields": "schedules,channel,title,id,events,channelId,start,finish,program,logo,sizes,src",
                    #                     "duration": 96400,
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
        with open(self.yatv_file_json, 'ab+') as fp:
            fp.write('[')
            m = _yparams["channelProgramsLimit"] / _yparams["channelLimit"]
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
                    log.error(fmt('update_yatv error: {0}', e))
            fp.write(']')
            fp.seek(0)
            self.jdata = json.load(fp)

    def get_finish(self):
        m = None
        for p in self.jdata:
            for sch in p['schedules']:
                try:
                    cm = self.strptime(sch['finish'].split('+')[0])
                    if not m or m > cm:
                        m = cm
                except Exception as e:
                    pass
        if not m:
            return datetime.datetime.now()
        return m

    def strptime(self, date_string):
        try:
            return datetime.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
        except TypeError:
            return datetime.datetime(*(time.strptime(date_string, "%Y-%m-%dT%H:%M:%S")[0:6]))

    def get_epg_by_id(self, chid):
        if chid is None or chid not in self.availableChannels["availableChannelsIds"]:
            return
        ctime = datetime.datetime.now()
        offset = int(round((ctime - datetime.datetime.utcnow()).total_seconds()) / 3600)
        for p in self.jdata:
            for sch in p['schedules']:
                if sch['channel']['id'] == chid:
                    for evt in sch['events']:
                        ep = {}
                        bt = evt['start'].split('+')
                        bt = self.strptime(bt[0]) + datetime.timedelta(hours=-3 + offset)
#                         bt = self.strptime(bt[0])
                        ep['btime'] = time.mktime(bt.timetuple())
                        et = evt['finish'].split('+')
                        et = self.strptime(et[0]) + datetime.timedelta(hours=-3 + offset)
#                         et = self.strptime(et[0])
                        ep['etime'] = time.mktime(et.timetuple())
                        ep['name'] = evt['program']['title']

                        yield ep

    def get_id_by_name(self, name):
        name = utils.lower(name, 'utf8')
        for p in self.jdata:
            for sch in p['schedules']:
                if utils.lower(sch['channel']['title'], 'utf8') == name:
                    return sch['channel']['id']

    def get_epg_by_name(self, name):
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
        return self.get_logo_by_id(self.get_id_by_name(name))


if __name__ == '__main__':
    pass

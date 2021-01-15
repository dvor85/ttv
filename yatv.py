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
from utils import uni, str2int, fs_str, makedirs
from six import itervalues


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
    else:
        return name, None


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
        self.jdata = {}
        self.update_timer = None
        self.yatv_path = os.path.join(defines.CACHE_PATH, 'yatv')
        self.yatv_logo_path = os.path.join(defines.CACHE_PATH, 'logo')
        self.sess = requests.Session()
        makedirs(fs_str(self.yatv_path))

        self.availableChannels = self.get_availible_channels()
        self.limit_channels = 24
        self.pages = int(round(self.availableChannels["availableChannels"] / self.limit_channels))
        self._get_jdata()

        log.d('stop initialization')

    def _get_jdata(self):
        for page in range(0, self.pages):
            if defines.isCancel():
                self.cancel()
                return
            self.update_yatv(page)
            yatv_file = os.path.join(self.yatv_path, "{0}.gz".format(page))
            if page not in self.jdata:
                bt = time.time()
                self.update_yatv(page)
                log.d("Loading yatv {y} in {t} sec".format(y=yatv_file, t=time.time() - bt))

                try:
                    bt = time.time()
                    with gzip.open(fs_str(yatv_file), 'rb') as fp:
                        self.jdata[page] = json.load(fp)
                    log.d("Loading yatv {y} from json in {t} sec".format(y=yatv_file, t=time.time() - bt))
                except Exception as e:
                    log.e("Error while loading json from {y}: {e}".format(y=yatv_file, e=uni(e)))
                    if os.path.exists(fs_str(yatv_file)):
                        os.unlink(fs_str(yatv_file))
                    raise e

        interval = (datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=1),
                                              datetime.time(3, 0)) - datetime.datetime.now()).seconds
        self.update_timer = Timer(interval, self._get_jdata)
        self.update_timer.name = "update_yatv_timer"
        self.update_timer.daemon = False
        self.update_timer.start()

    def update_yatv(self, page=0):
        yatv_file = os.path.join(self.yatv_path, "{0}.gz".format(page))

        valid_date = os.path.exists(fs_str(yatv_file)) and \
            datetime.date.today() == datetime.date.fromtimestamp(os.path.getmtime(fs_str(yatv_file)))
        if not valid_date:
            ncrd = uni(int(time.time()) * 1000 + 1080)
            dtm = uni(time.strftime('%Y-%m-%d'))

            url = 'https://m.tv.yandex.ru/ajax/i-tv-region/get'
            """
            https://tv.yandex.ru/ajax/i-tv-region/get?params={"duration":96400,"fields":"schedules,channel,title,id,events,channelId,start,finish,program,availableChannels,availableChannelsIds"}&resource=schedule&lang=ru&userRegion=193
            """

            _yparams = {"fields": "schedules,channel,title,id,events,description,channelId,start,finish,program,logo,sizes,src,images",
                        "channelLimit": self.limit_channels,
                        "channelProgramsLimit": self.availableChannels["availableChannels"],
                        "channelOffset": page * self.limit_channels,
                        "start": dtm + 'T03:00:00+03:00'
                        }
            _params = {
                "userRegion": 193,
                "resource": "schedule",
                "ncrd": ncrd,
                "params": json.dumps(_yparams),
                "lang": "ru"
            }

            with gzip.open(fs_str(yatv_file), 'wb') as fp:
                try:
                    r = defines.request(url, params=_params, session=self.sess, headers={'Referer': 'https://tv.yandex.ru/'})
                    fp.write(r.content)
                    YATV._lock.clear()
                except Exception as e:
                    log.error('update_yatv error: {0}'.format(e))

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
        _params = {
            "userRegion": 193,
            "resource": "schedule",
            "ncrd": ncrd,
            "params": json.dumps(_yparams),
            "lang": "ru"
        }
        r = defines.request(url, params=_params, session=self.sess, headers={'Referer': 'https://tv.yandex.ru/'})
        return r.json()

    def get_epg_by_id(self, chid, epg_offset=None):
        if chid is None or chid not in self.availableChannels["availableChannelsIds"]:
            return
        ctime = datetime.datetime.now()
        offset = round((ctime - datetime.datetime.utcnow()).total_seconds() / 3600) if epg_offset is None else epg_offset
        for p in itervalues(self.jdata):
            for sch in p['schedules']:
                if sch['channel']['id'] == chid:
                    for evt in sch['events']:
                        ep = {}
                        bt = evt['start'].split('+')
                        bt = strptime(bt[0]) + datetime.timedelta(hours=-3 + offset)
                        ep['btime'] = time.mktime(bt.timetuple())
                        et = evt['finish'].split('+')
                        et = strptime(et[0]) + datetime.timedelta(hours=-3 + offset)
                        ep['etime'] = time.mktime(et.timetuple())
                        ep['name'] = evt['program']['title']
                        ep['desc'] = evt['program'].get('description', '')
                        if 'images' in evt['program']:
                            ep['screens'] = ['http:{src}'.format(src=x['sizes']['200']['src']) for x in evt['program']['images']]

                        yield ep

    def get_id_by_name(self, name):
        names = [name.lower()]
        names.extend(CHANNEL_INFO.get(names[0], {}).get("aliases", []))
        for p in itervalues(self.jdata):
            for sch in p['schedules']:
                if sch['channel']['title'].lower() in names:
                    return sch['channel']['id']

    def get_epg_by_name(self, name):
        name_offset = get_name_offset(name)
        return self.get_epg_by_id(self.get_id_by_name(name_offset[0]), name_offset[1])

    def get_logo_by_id(self, chid):
        if chid is None or chid not in self.availableChannels["availableChannelsIds"]:
            return ''
        for p in itervalues(self.jdata):
            for sch in p['schedules']:
                if sch['channel']['id'] == chid:
                    if 'logo' in sch['channel']:
                        return 'http:{src}'.format(src=sch['channel']['logo']['sizes']["160"]["src"])
        return ''

    def get_logo_by_name(self, name):
        name_offset = get_name_offset(name)
        return self.get_logo_by_id(self.get_id_by_name(name_offset[0]))


if __name__ == '__main__':
    pass

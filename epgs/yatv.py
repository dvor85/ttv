# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import datetime
import gzip
import json
import time
from threading import Event, Lock, Semaphore
import requests
import defines
import logger
from pathlib import Path
from sources.channel_info import ChannelInfo
from epgs.epgtv import EPGTV, strptime


log = logger.Logger(__name__)


class YATV(EPGTV):
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
        EPGTV.__init__(self, 'yatv')
        self.jdata = {}
        self.update_timer = None
        self.sess = requests.Session()
        self.lock = Lock()
        self.chinfo = ChannelInfo.get_instance()
        self.sema = Semaphore(8)

        self.availableChannels = self.get_availible_channels()
        self.limit_channels = 24
        self.pages = int(round(self.availableChannels["availableChannels"] / self.limit_channels))
        self.get_jdata()

        log.d('stop initialization')

    def get_jdata(self):
        threads = []
        bt = time.time()
        with self.lock:
            for page in range(0, self.pages):
                if defines.isCancel():
                    return
                threads.append(defines.MyThread(self.update_epg, page=page))

            for t in threads:
                t.start()
            for t in threads:
                t.join()
        log.d("Loading yatv in {t} sec".format(t=time.time() - bt))
        return self.jdata

    def update_epg(self, page=0):
        yatv_file = Path(self.epgtv_path, f"{page}.gz")
        valid_date = yatv_file.exists() and datetime.date.today() == datetime.date.fromtimestamp(yatv_file.stat().st_mtime)
        if not valid_date:
            ncrd = str(int(time.time()) * 1000 + 1080)
            dtm = str(time.strftime('%Y-%m-%d'))

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

            with self.sema:
                with gzip.open(yatv_file, 'wb') as fp:
                    try:
                        r = defines.request(url, params=_params, session=self.sess, headers={'Referer': 'https://tv.yandex.ru/'})
                        fp.write(r.content)
                        self.jdata[page] = r.json()
                    except Exception as e:
                        log.error('update_yatv error: {0}'.format(e))
        if page not in self.jdata:
            try:
                bt = time.time()
                with gzip.open(yatv_file, 'rb') as fp:
                    self.jdata[page] = json.load(fp)
                log.d(f"Loading yatv json from {yatv_file} in {time.time() - bt} sec")
            except Exception as e:
                log.e(f"Error while loading json from {yatv_file}: {e}")
                yatv_file.unlink(missing_ok=True)

    def get_yatv_sess(self):
        return self.sess

    def get_availible_channels(self):
        ncrd = str(int(time.time()) * 1000 + 1080)
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
        for p in self.get_jdata().values():
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
        for n in names:
            chinfo = self.chinfo.get_info_by_name(n)
            if chinfo:
                names.append(chinfo['title'])
                break
        return next((sch['channel']['id'] for p in self.get_jdata().values() for sch in p['schedules'] and sch['channel']['title'].lower() in names), None)

    def get_logo_by_id(self, chid):
        if chid is None or chid not in self.availableChannels["availableChannelsIds"]:
            return ''
        for p in self.get_jdata().values():
            for sch in p['schedules']:
                if sch['channel']['id'] == chid:
                    if 'logo' in sch['channel']:
                        return 'http:{src}'.format(src=sch['channel']['logo']['sizes']["160"]["src"])
        return ''


if __name__ == '__main__':
    pass

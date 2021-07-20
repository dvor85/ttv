# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import datetime
import gzip
import json
import os
import time
from threading import Event, Lock
import requests
import defines
import logger
from sources.channel_info import CHANNEL_INFO
from utils import uni, fs_str
from six import itervalues
from epgs.epgtv import EPGTV
import re
# from difflib import SequenceMatcher as SM


log = logger.Logger(__name__)
_tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')
_spec_re = re.compile(r'&(nbsp|laquo|raquo|mdash|ndash|quot);')


class MAILTV(EPGTV):
    _instance = None
    _lock = Event()

    @staticmethod
    def get_instance():
        if MAILTV._instance is None:
            if not MAILTV._lock.is_set():
                MAILTV._lock.set()
                try:
                    MAILTV._instance = MAILTV()
                except Exception as e:
                    log.error("get_instance error: {0}".format(e))
                    MAILTV._instance = None
                finally:
                    MAILTV._lock.clear()
        return MAILTV._instance

    def __init__(self):
        EPGTV.__init__(self, 'mailtv')
        self.jdata = {}
        self.update_timer = None

        self.sess = requests.Session()
        self.lock = Lock()
        self.ex_channels = []
        self.need_update = True

        self.get_jdata()

        log.d('stop initialization')

    def get_jdata(self):
        bt = time.time()
        page = 0

        with self.lock:
            for p in os.listdir(self.epgtv_path):
                if defines.isCancel():
                    return
                _f = os.path.join(self.epgtv_path, p)
                valid_date = os.path.exists(fs_str(_f)) and datetime.date.today() == datetime.date.fromtimestamp(os.path.getmtime(fs_str(_f)))
                self.need_update = self.need_update and not valid_date
                if not self.need_update:
                    page = p.replace('.gz', '')
                    self.update_epg(page)
                else:
                    os.unlink(_f)

            while self.need_update:
                if defines.isCancel():
                    return
                self.update_epg(page)
                page += 1

        log.d("Loading mailtv in {t} sec".format(t=time.time() - bt))
        return self.jdata

    def update_epg(self, page=0):

        mailtv_file = os.path.join(self.epgtv_path, "{0}.gz".format(page))
        valid_date = os.path.exists(fs_str(mailtv_file)) and \
            datetime.date.today() == datetime.date.fromtimestamp(os.path.getmtime(fs_str(mailtv_file)))
        if not valid_date:
            dtm = uni(time.strftime('%Y-%m-%d'))

            url = 'https://tv.mail.ru/ajax/index/'

            _params = {"region_id": 70,
                       "channel_type": "all",
                       "appearance": "list",
                       "period": "all",
                       "date": dtm,
                       "ex": self.ex_channels
                       }

            with gzip.open(fs_str(mailtv_file), 'w') as fp:
                try:
                    r = defines.request(url, method='post', params=_params, session=self.sess,
                                        headers={'Referer': 'https://tv.mail.ru/'})

                    self.need_update = r.ok
                    if r.ok:
                        self.jdata[page] = r.json()
                        status = self.jdata[page].get('status', '').lower()
                        log.d('status={}'.format(status))
                        if status == 'ok':
                            fp.write(r.content)
                        else:
                            del self.jdata[page]

                except Exception as e:
                    log.error('update_mailtv error: {0}'.format(e))

            if page in self.jdata:
                for sch in self.jdata[page]['schedule']:
                    if sch['channel']['id'] not in self.ex_channels:
                        self.ex_channels.append(sch['channel']['id'])
                self.need_update = bool(self.jdata[page]['pager']['next']['url'])
            else:
                self.need_update = False

        if page not in self.jdata:
            try:
                bt = time.time()
                with gzip.open(fs_str(mailtv_file), 'r') as fp:
                    self.jdata[page] = json.load(fp)
                log.d("Loading mailtv json from {y} in {t} sec".format(y=mailtv_file, t=time.time() - bt))
            except Exception as e:
                log.e("Error while loading json from {y}: {e}".format(y=mailtv_file, e=uni(e)))
                if os.path.exists(fs_str(mailtv_file)):
                    os.unlink(fs_str(mailtv_file))

    def get_sess(self):
        return self.sess

    def get_epg_by_id(self, chid, epg_offset=None):
        if chid is None:  # or chid not in self.availableChannels["availableChannelsIds"]:
            return
        ctime = datetime.datetime.now()
        offset = round((ctime - datetime.datetime.utcnow()).total_seconds() / 3600) if epg_offset is None else epg_offset
        bt = None
        ep = None
        for p in itervalues(self.get_jdata()):
            for sch in p['schedule']:
                if sch['channel']['id'] == chid:
                    for evt in sch['event']:

                        bt = list(map(int, evt['start'].split(':')))
                        bt = datetime.datetime.fromordinal(
                            (ctime.date().toordinal())) + datetime.timedelta(hours=bt[0], minutes=bt[1]) + datetime.timedelta(hours=-3 + offset)
                        if ep is not None:
                            ep['etime'] = time.mktime(bt.timetuple())
                        ep = {}

                        ep['btime'] = time.mktime(bt.timetuple())
                        ep['name'] = evt['name']
                        ep['event_id'] = evt['id']

                        yield ep

    def get_event_info(self, event_id):
        info = {}
        url = 'https://tv.mail.ru/ajax/event/'
        _params = {"region_id": 70,
                   "id": event_id
                   }
        r = defines.request(url, method='post', params=_params, session=self.sess,
                            headers={'Referer': 'https://tv.mail.ru/'}, trys=1, timeout=1)

        if r.ok:
            j = r.json()
            if j.get('status', '').lower() == 'ok':
                if 'tv_event' in j:
                    info['desc'] = _spec_re.sub(' ', _tag_re.sub('', j['tv_event'].get('descr', '')))
                    info['screens'] = [j['tv_event'].get('sm_image_url', ''),
                                       j['tv_event']['channel'].get('pic_url_64', '')]
        return info

    def get_id_by_name(self, name):
        names = [name.lower(), name.lower().replace('-', ' ')]
        names.extend(CHANNEL_INFO.get(names[0], {}).get("aliases", []))
        for p in itervalues(self.get_jdata()):
            for sch in p['schedule']:
                # if SM(isjunk=None, a=name.lower(), b=sch['channel']['name'].lower(), autojunk=True).quick_ratio() > 0.85:
                #     return sch['channel']['id']
                if sch['channel']['name'].lower() in names:
                    return sch['channel']['id']
                elif len(name) > 8:
                    for n in names:
                        if n in sch['channel']['name'].lower():
                            return sch['channel']['id']

    def get_logo_by_id(self, chid):
        if chid is None:  # or chid not in self.availableChannels["availableChannelsIds"]:
            return ''
        for p in itervalues(self.get_jdata()):
            for sch in p['schedule']:
                if sch['channel']['id'] == chid:
                    return sch['channel'].get('pic_url', '')
        return ''


if __name__ == '__main__':
    pass

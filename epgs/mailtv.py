# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import datetime
import gzip
import json
import time
from threading import Event, Lock
import requests
import defines
import logger
from sources.channel_info import ChannelInfo
from epgs.epgtv import EPGTV
import re

log = logger.Logger(__name__)
_tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')
_spec_re = re.compile(r'&(nbsp|laquo|raquo|mdash|ndash|quot);')


class MAILTV(EPGTV):
    _instance = None
    _lock = Event()

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
        EPGTV.__init__(self, 'mailtv')
        self.jdata = {}
        self.update_timer = None

        self.sess = requests.Session()
        self.lock = Lock()
        self.ex_channels = set()
        self.need_update = True

        self.get_jdata()
        self.chinfo = ChannelInfo().get_instance()

        log.d('stop initialization')

    def get_jdata(self):
        bt = time.time()
        page = 0

        with self.lock:
            for _f in self.epgtv_path.glob('*.gz'):
                if defines.isCancel():
                    return
                valid_date = _f.exists() and datetime.date.today() == datetime.date.fromtimestamp(_f.stat().st_mtime)
                self.need_update = self.need_update and not valid_date
                if not self.need_update:
                    self.update_epg(_f.stem)
                else:
                    _f.unlink()

            while self.need_update:
                if defines.isCancel():
                    return
                self.update_epg(page)
                page += 1

        log.d(f"Loading mailtv in {time.time() - bt} sec")
        return self.jdata

    def update_epg(self, page=0):
        mailtv_file = self.epgtv_path / f"{page}.gz"
        valid_date = mailtv_file.exists() and datetime.date.today() == datetime.date.fromtimestamp(mailtv_file.stat().st_mtime)
        if not valid_date:
            dtm = time.strftime('%Y-%m-%d')
            url = 'https://tv.mail.ru/ajax/index/'
            _params = {"region_id": 70,
                       "channel_type": "all",
                       "appearance": "list",
                       "period": "all",
                       "date": dtm,
                       "ex": self.ex_channels
                       }

            with gzip.open(mailtv_file, 'w+') as fp:
                try:
                    r = defines.request(url, method='post', params=_params, session=self.sess, headers={'Referer': 'https://tv.mail.ru/'})
                    self.need_update = r.ok
                    if r:
                        self.jdata[page] = r.json()
                        status = self.jdata[page].get('status', '').lower()
                        log.d(f'status={status}')
                        if status == 'ok':
                            fp.write(r.content)
                        else:
                            del self.jdata[page]

                except Exception as e:
                    log.error(f'update_mailtv error: {e}')

            if page in self.jdata:
                self.ex_channels.update(sch['channel']['id'] for sch in self.jdata[page]['schedule'])
                self.need_update = bool(self.jdata[page]['pager']['next']['url'])
            else:
                self.need_update = False

        if page not in self.jdata:
            try:
                bt = time.time()
                with gzip.open(mailtv_file, 'r') as fp:
                    self.jdata[page] = json.load(fp)
                log.d(f"Loading mailtv json from {mailtv_file} in {time.time() - bt} sec")
            except Exception as e:
                log.e(f"Error while loading json from {mailtv_file}: {e}")
                mailtv_file.unlink(missing_ok=True)

    def get_sess(self):
        return self.sess

    def get_epg_by_id(self, chid, epg_offset=None):
        if chid is None:  # or chid not in self.availableChannels["availableChannelsIds"]:
            return
        ctime = datetime.datetime.now()
        offset = round((ctime - datetime.datetime.utcnow()).total_seconds() / 3600) - 3
        if epg_offset is not None:
            offset -= epg_offset
#         log.d(f"offset {chid} = {offset}")
        bt = None
        ep = None
        for p in self.get_jdata().values():
            for sch in p['schedule']:
                if sch['channel']['id'] == chid:
                    for evt in sch['event']:

                        bt = list(map(int, evt['start'].split(':')))
                        bt = datetime.datetime.fromordinal(
                            (ctime.date().toordinal())) + datetime.timedelta(hours=bt[0], minutes=bt[1]) + datetime.timedelta(hours=offset)
                        if ep is not None:
                            ep['etime'] = time.mktime(bt.timetuple())
                        ep = {}

                        ep['btime'] = time.mktime(bt.timetuple())
                        ep['name'] = _spec_re.sub(' ', _tag_re.sub('', evt['name']))
                        ep['event_id'] = evt['id']

                        yield ep

    def get_event_info(self, event_id):
        info = {}
        url = 'https://tv.mail.ru/ajax/event/'
        _params = {"region_id": 70,
                   "id": event_id
                   }
        r = defines.request(url, method='post', params=_params, session=self.sess, headers={'Referer': 'https://tv.mail.ru/'}, trys=1, timeout=1)

        if r:
            j = r.json()
            if j.get('status', '').lower() == 'ok':
                if 'tv_event' in j:
                    info['desc'] = _spec_re.sub(' ', _tag_re.sub('', j['tv_event'].get('descr', '')))
                    info['screens'] = [j['tv_event'].get('sm_image_url', ''),
                                       j['tv_event']['channel'].get('pic_url_64', j['tv_event']['channel'].get('pic_url', ''))]
        return info

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

        for p in self.get_jdata().values():
            for sch in p['schedule']:
                if sch['channel']['name'].lower() in names:
                    return sch['channel']['id']
                # else:
                #     for a in names:
                #         b = sch['channel']['name'].lower()
                #         if sum(i == j for i, j in zip_longest(a, b))/max(len(a), len(b)) > 0.6:
                #             return sch['channel']['id']
                # elif len(name) > 8:
                #     for n in names:
                #         if n in sch['channel']['name'].lower():
                #             return sch['channel']['id']

    def get_logo_by_id(self, chid):
        if chid is None:  # or chid not in self.availableChannels["availableChannelsIds"]:
            return ''
        for p in self.get_jdata().values():
            for sch in p['schedule']:
                if sch['channel']['id'] == chid:
                    return sch['channel'].get('pic_url_64', sch['channel'].get('pic_url', ''))
        return ''


if __name__ == '__main__':
    pass

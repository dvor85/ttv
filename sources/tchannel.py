# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import datetime
import time
from pathlib import Path
from collections import UserDict
import defines
import logger
from epgs import epgtv
from epgs.epglist import Epg
from .channel_info import ChannelInfo

log = logger.Logger(__name__)


def sign(num):
    return "+" if num > 0 else "-"


class MChannel(UserDict):

    def __init__(self, chs=None):
        UserDict.__init__(self)
        if chs is None:
            chs = {}
        self.data.update(chs)

    def insert(self, index, ch):
        if self.title() != ch.title():
            for pu in self.xurl():
                for u in pu[1].values():
                    if ch['url']:
                        for cu in ch['url'].values():
                            if isinstance(u['url'], str) and isinstance(cu['url'], str) and u['url'] == cu['url']:
                                return
        if not isinstance(ch, self.__class__):
            while index in self.data:
                index += 1
            UserDict.__setitem__(self, index, ch)
        else:
            UserDict.update(ch)

    def xurl(self):
        """
        [src_name, {player: {url, mode}}]
        """
        return [(ch.src(), ch['url']) for ch in self.data.values() if ch['url']]

    def is_availible(self):
        return any(ch.is_availible() for ch in self.data.values())

    def enabled(self):
        return any(ch.enabled() for ch in self.data.values())

    def group(self):
        return next((ch.group() for ch in self.data.values() if ch.group()), None)

    def logo(self):
        return next((ch.logo() for ch in self.data.values() if ch.logo()), '')

    def id(self):
        return next((ch.id() for ch in self.data.values() if ch.id()), None)

    def name(self):
        return next((ch.name() for ch in self.data.values() if ch.name()), '')

    def pin(self):
        return next((ch.get('pin') for ch in self.data.values() if ch.get('pin')), None)

    def title(self):
        return next((ch.title() for ch in self.data.values() if ch.title()), None)

    def epg(self):
        fep = None
        for ch in self.data.values():
            ep = ch.epg()
#             Если нет описания, посмотреть в другом источнике
            if ep:
                fep = ep
                if 'event_id' in ep[0] or 'screens' in ep[0] or 'desc' in ep[0]:
                    return ep
        return fep


class TChannel(UserDict):

    def __init__(self, data=None, *args, **kwargs):
        UserDict.__init__(self, *args, **kwargs)
        if data is None:
            data = {}
        self.data.update(data)
        self.data.update(kwargs)
        self.logo_path = Path(defines.CACHE_PATH, 'logo')
        self.logo_path.mkdir(parents=True, exist_ok=True)
        self.chinfo = ChannelInfo().get_instance()

    def src(self):
        return self.get('src', 'undefined')

    def player(self):
        return self.get('player', 'undefined')

    def __getitem__(self, key):
        if key == 'url':
            if not isinstance(self.data.get(key), dict):
                self.data[key] = {self.player(): {'url': self.data.get(key), 'mode': self.get('mode', 'PID')}}

        return UserDict.__getitem__(self, key)

    def is_availible(self):
        return any(url_mode.get('availible', True) for url_mode in self['url'].values())

    def _get_group_title(self, groupname):
#         log.d(f"_get_group_title {groupname}")
        grinfo = self.chinfo.get_group_by_name(groupname)
        if grinfo:
            return grinfo['group_title'] if grinfo['group_title'] else groupname
        return groupname

    def enabled(self):
#         name = epgtv.get_name_offset(self.title().lower())[0]
        chinfo = self.chinfo.get_channel_by_name(self.name().lower())
        return chinfo['ch_enable'] if chinfo else True

    def group(self):
        if not self.get('groupname'):
            name = epgtv.get_name_offset(self.title().lower())[0]
            chinfo = self.chinfo.get_channel_by_name(name)
            if chinfo and chinfo['group_name']:
                gr = chinfo['group_title'] if chinfo.get('group_title') else chinfo['group_name']
            else:
                gr = self._get_group_title(self.get('cat'))

            self.data['groupname'] = gr.capitalize() if gr else None
        return self.get('groupname')

    def logo(self, session=None):
        name = epgtv.get_name_offset(self.title().lower())[0]
        f_logo = Path(self.logo_path, f"{name}.png")
        logo_url = None
        epg = None
        if f_logo.exists():
            self.data['logo'] = str(f_logo)
            return str(f_logo)
        if not self.get('logo'):
            epg = Epg().link
            if epg is not None:
                logo_url = epg.get_logo_by_name(self.title())
        elif '://' in self.get('logo'):
            logo_url = self.get('logo')

        try:
            if logo_url:
                _sess = epg.get_sess() if epg else session
                r = defines.request(logo_url, session=_sess)
                if r.ok:
                    f_logo.write_bytes(r.content)
                    self.data['logo'] = str(f_logo)
                    return str(f_logo)
        except Exception as e:
            log.e(f'update_logo error {e}')

        return str(self.get('logo'))

    def id(self):
        return self.get('id', self.name())

    def name(self):
        return self.get('name')

    def title(self):
        if not self.get('title'):
            name_offset = epgtv.get_name_offset(self.name().lower())
            self.data['title'] = name_offset[0].capitalize()
            chinfo = self.chinfo.get_channel_by_name(name_offset[0])
            if chinfo and chinfo.get('ch_title'):
                self.data['title'] = chinfo['ch_title'].capitalize()
            if name_offset[1]  and sign(name_offset[1]):
                self.data['title'] += " ({sign}{offset})".format(sign=sign(name_offset[1]), offset=name_offset[1])

        return self.get('title')

    def update_epglist(self):
        try:
            epg = Epg().link
            if not self.get('epg') and epg is not None:
                self.data['epg'] = list(epg.get_epg_by_name(self.title()))
        except Exception as e:
            log.e(f'update_epglist error {e}')

    def epg(self):
        """
        :return [{name, btime, etime},]
        """

        try:
            defines.MyThread(self.update_epglist).start().join(4)
            ctime = datetime.datetime.now()
            prev_x = {}
            curepg = []
            for x in self.get('epg', {}):
                try:
                    bt = datetime.datetime.fromtimestamp(float(x['btime']))
                    if prev_x and 'etime' not in prev_x:
                        prev_x['etime'] = x['btime']
                    if abs((bt - ctime).days) <= 1 and float(x['btime']) >= float(prev_x.get('etime', 0)) and \
                            (float(x.get('etime', 0)) >= time.time()):
                        curepg.append(x)
                    prev_x = x

                except Exception as e:
                    log.error(e)

            self.data['epg'] = curepg
        except Exception as e:
            log.e(f'epg error {e}')

        return self.get('epg')


class TChannels:

    def __init__(self, name, reload_interval=-1, lock=None):
        self.name = name
        self.lock = lock
        self.channels = []
        self.reload_interval = reload_interval

    def update_channels(self):
        raise NotImplementedError

    def get_channels(self):
        """
        :return [TChannel(),]
        """
        self.update_channels()
        return self.channels

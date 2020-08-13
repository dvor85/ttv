# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import datetime
import os

from six.moves import UserDict, UserList
from six import iteritems, itervalues
from utils import uni, str2

import defines
import logger
import yatv
from .channel_info import CHANNEL_INFO
from .grouplang import translate
from utils import str2int
# from .table import channel_sources


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
                for u in itervalues(pu[1]):
                    if ch['url']:
                        for cu in itervalues(ch['url']):
                            if isinstance(u[0], unicode) and isinstance(cu[0], unicode):
                                if u[0] == cu[0]:
                                    return
        if not isinstance(ch, self.__class__):
            while index in self.data:
                index += 1
            UserDict.__setitem__(self, index, ch)
        else:
            UserDict.update(ch)

    def group(self):
        for ch in itervalues(self.data):
            gr = ch.group()
            if gr:
                return gr

    def xurl(self):
        """
        [src_name, {player: (url, mode)}]
        """
        ret = []

        for ch in itervalues(self.data):
            if ch['url']:
                ret.append([ch.src(), ch['url']])
        return ret

    def logo(self):
        for ch in itervalues(self.data):
            lo = ch.logo()
            if lo:
                return lo

    def name(self):
        for ch in itervalues(self.data):
            nm = ch.name()
            if nm:
                return nm

    def pin(self):
        for ch in itervalues(self.data):
            p = ch.get('pin')
            if p:
                return p

    def title(self):
        for ch in itervalues(self.data):
            tit = ch.title()
            if tit:
                return tit

    def epg(self):
        fep = None
        for ch in itervalues(self.data):
            ep = ch.epg()
#             Если нет описания, посмотреть в другом источнике
            if ep:
                fep = ep
                if ep[0].get('desc'):
                    return ep
        return fep

    def get_screenshots(self):
        for ch in itervalues(self.data):
            screens = ch.get_screenshots()
            if screens:
                return screens


class TChannel(UserDict):

    def __init__(self, data=None, *args, **kwargs):
        UserDict.__init__(self, *args, **kwargs)
        if data is None:
            data = {}
        self.data.update(data)
        self.data.update(kwargs)
        self.yatv_logo_path = os.path.join(defines.CACHE_PATH, 'logo')
        if not os.path.exists(self.yatv_logo_path):
            os.mkdir(self.yatv_logo_path)

    def src(self):
        return self.get('src', 'undefined')

    def player(self):
        return self.get('player', 'undefined')

    def __getitem__(self, key):
        if key == 'url':
            if not isinstance(self.data.get(key), dict):
                self.data[key] = {self.player(): (uni(self.data.get(key)), self.get('mode', 'PID'))}

        return UserDict.__getitem__(self, key)

#     def xurl(self):
#         if self.get('url') and not isinstance(self.get('url'), dict):
#             self.data['url'] = {
#                 self.player(): (uni(self.get('url')), self.get('mode'))
#             }
#         return self['url']

    def group(self):
        name = yatv.get_name_offset(self.name().lower())[0]
        gr = self.get('cat')
        if name in CHANNEL_INFO:
            gr = CHANNEL_INFO[name].get('cat')
        if gr:
            self.data['cat'] = translate.get(gr.lower(), gr)
        return uni(self.get('cat'))

    def logo(self, session=None):
        logo = os.path.join(self.yatv_logo_path, "{name}.png".format(name=self.title().lower()))
        logo_url = None
        epg = None
        if os.path.exists(logo):
            self.data['logo'] = logo
            return logo
        if not self.get('logo'):
            epg = yatv.YATV.get_instance()
            if epg is not None:
                logo_url = epg.get_logo_by_name(self.name())
        elif '://' in self.get('logo'):
            logo_url = self.get('logo')

        try:
            if logo_url:
                _sess = epg.get_yatv_sess() if epg else session
                r = defines.request(logo_url, session=_sess)
                if len(r.content) > 0:
                    with open(logo, 'wb') as fp:
                        fp.write(r.content)
                    self.data['logo'] = logo
        except Exception as e:
            log.e('update_logo error {0}'.format(e))

        return uni(self.get('logo'))

    def id(self):
        return uni(self.get('id', self.name()))

    def name(self):
        return uni(self.get('name'))

    def title(self):
        if not self.get('title'):
            name_offset = yatv.get_name_offset(self.name().lower())
            ctime = datetime.datetime.now()
            offset = round((ctime - datetime.datetime.utcnow()).total_seconds() / 3600)
            if name_offset[0] in CHANNEL_INFO:
                self.data['title'] = CHANNEL_INFO[name_offset[0]].get('aliases', [name_offset[0]])[0].capitalize()
            else:
                self.data['title'] = name_offset[0].capitalize()
            if name_offset[1] and name_offset[1] != offset and sign(name_offset[1]):
                self.data['title'] += " ({sign}{offset})".format(sign=sign(name_offset[1]), offset=name_offset[1])
        return uni(self.data["title"])

    def update_epglist(self):
        try:
            #             if defines.platform()['os'] == 'linux':
            #                 epg = xmltv.XMLTV.get_instance()
            #             else:
            epg = yatv.YATV.get_instance()
            if not self.get('epg') and epg is not None:
                self.data['epg'] = []
                for ep in epg.get_epg_by_name(self.name()):
                    self.data['epg'].append(ep)
        except Exception as e:
            log.e('update_epglist error {0}'.format(e))

    def epg(self):
        """
        :return [{name, btime, etime},]
        """

        try:
            thr = defines.MyThread(self.update_epglist)
            thr.start()
            thr.join(4)
            ctime = datetime.datetime.now()
            prev_bt = 0
            prev_et = 0
            curepg = []
            for x in self.get('epg', []):
                try:
                    bt = datetime.datetime.fromtimestamp(float(x['btime']))
                    et = datetime.datetime.fromtimestamp(float(x['etime']))
                    if et > ctime and abs((bt - ctime).days) <= 1 and prev_et <= float(x['btime']) > prev_bt:
                        curepg.append(x)
                        prev_bt = float(x['btime'])
                        prev_et = float(x['etime'])
                except Exception as e:
                    log.error(e)
            self.data['epg'] = curepg
        except Exception as e:
            log.e('epg error {0}'.format(e))

        return self.get('epg')

    def get_screenshots(self):
        pass


class TChannels:

    def __init__(self, name, reload_interval=-1, lock=None):
        self.name = name
        self.lock = lock
        self.channels = []
        self.reload_interval = reload_interval

    def update_channels(self):
        self.channels = []

    def get_channels(self):
        """
        :return [TChannel(),]
        """
        self.update_channels()
        return self.channels

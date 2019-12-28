# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import datetime
import os

from six.moves import UserDict
from utils import uni, str2

import defines
import logger
import yatv
from .channel_info import CHANNEL_INFO
from .grouplang import translate

log = logger.Logger(__name__)


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
        return self.data.get('src', 'undefined')

    def player(self):
        return self.data.get('player', 'undefined')

    def xurl(self):
        if self.data.get('url') and not isinstance(self.data.get('url'), dict):
            self.data['url'] = {
                self.player(): {
                    self.src(): uni(self.data.get('url'))
                }
            }
        return self.data.get('url')

    def group(self):
        name = yatv.get_name_offset(self.name().lower())[0]
        gr = self.data.get('cat')
        if name in CHANNEL_INFO:
            gr = CHANNEL_INFO[name].get('cat')
        if gr:
            self.data['cat'] = translate.get(gr.lower(), gr)
        return uni(self.data.get('cat'))

    def logo(self):
        name = self.name().lower()
        logo = os.path.join(self.yatv_logo_path, "{name}.png".format(name=name))
        if not self.data.get('logo'):
            if os.path.exists(logo):
                self.data['logo'] = logo
            else:
                self.data['logo'] = ''

        try:
            if not self.data.get('logo'):
                epg = yatv.YATV.get_instance()
                if epg is not None:
                    ylogo = epg.get_logo_by_name(name)
                    if ylogo:
                        r = defines.request(ylogo, session=epg.get_yatv_sess(), headers={'Referer': 'https://tv.yandex.ru/'})
                        with open(logo, 'wb') as fp:
                            fp.write(r.content)
                        self.data['logo'] = logo

        except Exception as e:
            log.e('update_logo error {0}'.format(e))

        return uni(self.data.get('logo'))

    def id(self):
        return uni(self.data.get('id', self.name()))

    def name(self):
        return uni(self.data.get('name'))

    def title(self):
        if not self.data.get('title'):
            name_offset = yatv.get_name_offset(self.name().lower())
            ctime = datetime.datetime.now()
            offset = round((ctime - datetime.datetime.utcnow()).total_seconds() / 3600)
            if name_offset[0] in CHANNEL_INFO:
                self.data['title'] = CHANNEL_INFO[name_offset[0]].get('aliases', [name_offset[0]])[0].capitalize()
            else:
                self.data['title'] = name_offset[0].capitalize()
            if name_offset[1] and name_offset[1] != offset and self.sign(name_offset[1]):
                self.data['title'] += " ({sign}{offset})".format(sign=self.sign(name_offset[1]), offset=name_offset[1])
        return uni(self.data["title"])

    def sign(self, num):
        return "+" if num > 0 else "-"

    def screenshots(self):
        """
        :return [{filename:url},...]
        """
        pass

    def update_epglist(self):
        try:
            #             if defines.platform()['os'] == 'linux':
            #                 epg = xmltv.XMLTV.get_instance()
            #             else:
            epg = yatv.YATV.get_instance()
            if not self.data.get('epg') and epg is not None:
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
            for x in self.data.get('epg', []):
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

        return self.data.get('epg')


class TChannels:

    def __init__(self, reload_interval=-1, prior=0):
        self.channels = []
        self.prior = prior
        self.reload_interval = reload_interval

    def update_channels(self):
        self.channels = []

    def get_channels(self):
        """
        :return [TChannel(),]
        """
        self.update_channels()
        return self.channels

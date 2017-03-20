# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from UserDict import UserDict
import datetime
import utils
import defines
import xmltv
import logger
import os
from channel_info import CHANNEL_INFO

fmt = utils.fmt
log = logger.Logger(__name__)


class TChannel(UserDict):

    def __init__(self, data={}):
        self.data = {}
        self.data['type'] = 'channel'
        self.data['mode'] = "PID"
        self.data['players'] = ['ace']
        self.data.update(data)

    def get_url(self, player=None):
        return self.data.get('url')

    def get_mode(self):
        return self.data.get('mode')

    def get_group(self):
        name = utils.lower(self.get_name(), 'utf8')
        if not self.data.get('cat'):
            try:
                self.data['cat'] = CHANNEL_INFO[name]['cat']
            except KeyError:
                self.data['cat'] = None
        return self.data['cat']

    def get_logo(self):
        name = utils.lower(self.get_name(), 'utf8')
        if not self.data.get('logo'):
            try:
                self.data['logo'] = CHANNEL_INFO[name]['logo']
            except KeyError:
                self.data['logo'] = ''

        if self.data.get('logo'):
            if ':' not in self.data['logo']:
                self.data['logo'] = utils.utf(fmt('http://{0}/uploads/{1}', 'torrent-tv.ru', self.data['logo']))
            else:
                self.data['logo'] = utils.utf(self.data['logo'])
        else:
            logo = fmt("{addon_path}/resources/logo/{name}.png",
                       addon_path=utils.utf(defines.ADDON_PATH), name=utils.utf(self.get_name()))
            if os.path.exists(logo):
                self.data['logo'] = logo

        return self.data.get('logo')

    def get_id(self):
        return utils.utf(fmt("{0}", self.data.get('id')))

    def get_name(self):
        return utils.utf(self.data.get('name'))

    def get_screenshots(self):
        """
        :return [{filename:url},...]
        """
        pass

    def update_epglist(self):
        try:
            xmltv_epg = xmltv.XMLTV.get_instance()
            if not self.data.get('epg') and xmltv_epg is not None:
                self.data['epg'] = []
                for ep in xmltv_epg.get_epg_by_name(self.get_name()):
                    self.data['epg'].append(ep)
        except Exception as e:
            log.e(fmt('update_epglist error {0}', e))

    def get_epg(self):
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
            log.e(fmt('get_epg error {0}', e))

        return self.data.get('epg')


class TChannels():

    def __init__(self, reload_interval=-1):
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

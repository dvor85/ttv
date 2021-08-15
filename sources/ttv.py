# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import defines
import time
import os
import json
from utils import uni, str2, str2int, fs_str
import requests
import logger
import uuid
from .tchannel import TChannel, TChannels

log = logger.Logger(__name__)
_server = 'ttv.run'
_sess = requests.Session()


class Channel(TChannel):

    def __init__(self, data={}, ttv_session=None):
        TChannel.__init__(self, data=data, src='ttv', player='ace,nox,tsp')
        self.use_nox = uni(defines.ADDON.getSetting('use_nox')) == 'true'
        self.use_ace = uni(defines.ADDON.getSetting('use_ace')) == 'true'
        self.use_tsproxy = uni(defines.ADDON.getSetting('use_tsproxy')) == 'true'
        self.ttv_session = ttv_session

    def __getitem__(self, key):
        if key == 'url':
            #             return None
            if not isinstance(self.data.get(key), dict):
                if self.use_ace:
                    self.data[key] = {'ace': (self._get_ace_url, self.get('mode'))}
                if self.use_nox:
                    self.data[key] = {'nox': (self._get_nox_url, self.get('mode'))}
                if self.use_tsproxy:
                    self.data[key] = {'tsproxy': (self._get_tsproxy_url, self.get('mode'))}

        return TChannel.__getitem__(self, key)

    def _get_ace_url(self):
        try:
            params = dict(
                session=self.ttv_session,
                channel_id=self.id(),
                typeresult='json')

            r = defines.request("http://{server}/v3/translation_stream.php".format(server='api.{0}'.format(_server)),
                                params=params, session=_sess, trys=1)
            jdata = r.json()
            self.data['mode'] = jdata["type"].upper().replace("CONTENTID", "PID")
            return jdata['source']
        except Exception as e:
            log.w('_get_ace_url error: {0}'.format(uni(e)))

    def _get_nox_url(self):
        nox_ip = defines.ADDON.getSetting('nox_ip')
        nox_port = str2int(defines.ADDON.getSetting('nox_port'))
        try:
            params = dict(
                session=self.ttv_session,
                channel_id=self.id(),
                typeresult='json')
            r = defines.request("http://{server}/v3/get_noxbit_cid.php".format(server='api.{0}'.format(_server)),
                                params=params, session=_sess, trys=1)

            jdata = r.json()
            if not jdata["success"]:
                return
            if jdata["success"] == 0:
                return
            cid = jdata["cid"]
            streamtype = uni(defines.ADDON.getSetting('nox_streamtype'))
            return "http://{nox_ip}:{nox_port}/{streamtype}?cid={cid}".format(
                nox_ip=nox_ip,
                nox_port=nox_port,
                streamtype=streamtype, cid=cid)
        except Exception as e:
            log.w('_get_nox_url error: {0}'.format(uni(e)))

    def _get_tsproxy_url(self):
        zoneid = 0
        nohls = 0 if defines.ADDON.getSetting("proxy_hls") == "true" else 1
        try:
            params = dict(
                session=self.ttv_session,
                channel_id=self.id(),
                typeresult='json',
                zone_id=zoneid,
                nohls=nohls)
            r = defines.request("http://{server}/v3/translation_http.php".format(server='api.{0}'.format(_server)),
                                params=params, session=_sess, trys=1)

            jdata = r.json()
            if not jdata["success"]:
                return
            if jdata["success"] == 0:
                return
            return jdata['source']
        except Exception as e:
            log.w('_get_tsproxy_url error: {0}'.format(uni(e)))

    def update_epglist(self):
        defines.MyThread(TChannel.update_epglist, self).start().join(4)
        if not self.get('epg'):
            try:
                params = dict(
                    session=self.ttv_session,
                    epg_id=self.get('epg_id'),
                    typeresult='json')
                r = defines.request('http://{server}/v3/translation_epg.php'.format(server='api.{0}'.format(_server)),
                                    params=params, session=_sess, trys=1)

                jdata = r.json()
                if str2int(jdata.get('success')) != 0:
                    self.data['epg'] = jdata['data']
            except Exception as e:
                log.d('update_epglist error: {0}'.format(uni(e)))

    def logo(self, *args):
        if self.get('logo') and '://' not in self.get('logo'):
            self.data['logo'] = 'http://{server}/uploads/{logo}'.format(server=_server, logo=uni(self.get('logo')))
        return TChannel.logo(self, session=_sess)

    def get_info(self):
        # Скрины пока не работают в ttv
        # return
        info = {}
        params = dict(
            session=self.ttv_session,
            channel_id=self.id(),
            count=2,
            typeresult='json')
        r = defines.request('http://{server}/v3/translation_screen.php'.format(server='api.{0}'.format(_server)),
                            params=params, session=_sess, trys=1)
        if r.ok:
            jdata = r.json()
            if str2int(jdata.get('success')) != 0 and not jdata.get('error'):
                info['screens'] = [x['filename'].replace('web1.1ttv.org', 'shot.{0}'.format(_server)) for x in jdata['screens']]

        return info


class Channels(TChannels):

    def __init__(self):
        self.user = {}
        self.ttv_session = None
        self._temp = os.path.join(defines.CACHE_PATH, "ttv.json")
        TChannels.__init__(self, name='ttv', reload_interval=86400)

    def _load_jdata(self, avail=True):
        log.d('get {temp}'.format(temp=self._temp))
        if os.path.exists(fs_str(self._temp)):
            if not avail or (time.time() - os.path.getmtime(fs_str(self._temp)) <= self.reload_interval):
                with open(fs_str(self._temp), 'r') as fp:
                    return json.load(fp)

    def _save_jdata(self, jdata):
        with open(fs_str(self._temp), 'w') as fp:
            json.dump(jdata, fp)

    def _initTTV(self):
        try:
            log.info("init TTV")
            guid = uni(defines.ADDON.getSetting("uuid"))
            if guid == '':
                guid = str(uuid.uuid1())
                defines.ADDON.setSetting("uuid", str2(guid))
            guid = guid.replace('-', '')

            try:
                params = dict(
                    username=uni(defines.ADDON.getSetting('ttv_login')),
                    password=uni(defines.ADDON.getSetting('ttv_password')),
                    typeresult='json',
                    application='xbmc',
                    guid=guid
                )
                r = defines.request('http://{server}/v3/auth.php'.format(server='api.{0}'.format(_server)),
                                    params=params, session=_sess, trys=1)
                jdata = r.json()
                if str2int(jdata.get('success')) == 0:
                    raise Exception("Auth error: {0}".format(uni(jdata.get('error'))))
            except Exception as e:
                log.e(uni(e))

            self.user = {"login": uni(defines.ADDON.getSetting('ttv_login')),
                         "balance": jdata.get("balance"),
                         "vip": jdata["balance"] > 1}

            self.ttv_session = jdata.get('session')
        except Exception as e:
            log.error("_initTTV error: {0}".format(uni(e)))

    def _get_groupname_by_id(self, categories, chid):
        if categories:
            for g in categories:
                if g.get('id') == chid:
                    return g.get("name")

    def update_channels(self):
        TChannels.update_channels(self)
        self._initTTV()
        jdata = dict()
        try:
            jdata = self._load_jdata()
            if not jdata:
                raise Exception("{temp} is empty".format(temp=self._temp))

        except Exception as e:
            log.debug("load_json_temp error: {0}".format(uni(e)))
            if self.ttv_session:
                try:
                    params = dict(
                        session=self.ttv_session,
                        type='channel',
                        typeresult='json')
                    r = defines.request('http://{server}/v3/translation_list.php'.format(server='api.{0}'.format(_server)),
                                        params=params, session=_sess, trys=1)

                    jdata = r.json()

                    if str2int(jdata.get('success')) == 0:
                        raise Exception(jdata.get('error'))
                    self._save_jdata(jdata)
                except Exception as e:
                    log.e('get_channels error: {0}'.format(uni(e)))
                    # log.i('Try to load previos channels, if availible')
                    # try:
                    #     jdata = self._load_jdata(False)
                    #     if not jdata:
                    #         raise Exception("Channels are not avalible")
                    # except Exception as e:
                    #     log.error(uni(e))

        if jdata.get('channels'):
            for ch in jdata['channels']:
                try:
                    if not (ch.get("name") or ch.get("id")):
                        continue

                    channel = ch
                    channel['cat'] = self._get_groupname_by_id(jdata.get("categories"), ch['group'])
                    self.channels.append(Channel(channel, self.ttv_session))
                except Exception as e:
                    log.e('Add channel error: {0}'.format(uni(e)))

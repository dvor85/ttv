# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import defines
from utils import uni, str2, str2int
import logger
import uuid
import os
from .tchannel import TChannel, TChannels

log = logger.Logger(__name__)
_servers = ['api.ttv.world']


class Channel(TChannel):

    def __init__(self, data={}, session=None):
        TChannel.__init__(self, data=data, src='ttv', player='ace,nox')
        self.use_nox = uni(defines.ADDON.getSetting('use_nox')) == 'true'
        self.use_ace = uni(defines.ADDON.getSetting('use_ace')) == 'true'
        self.session = session

    def __getitem__(self, key):
        log.d('access {0}'.format(key))
        if key == 'url':
            if not isinstance(self.data.get(key), dict):
                self.data[key] = {}
                if self.use_ace:
                    self.data[key]['ace'] = {
                        self.src(): self._get_ace_url(),
                    }
                if self.use_nox:
                    self.data[key]['nox'] = {
                        self.src(): self._get_nox_url(),
                    }
        return TChannel.__getitem__(self, key)

    def _get_ace_url(self):
        for server in _servers:
            try:
                params = dict(
                    session=self.session,
                    channel_id=self.id(),
                    typeresult='json')

                r = defines.request("http://{server}/v3/translation_stream.php".format(server=server),
                                    params=params, trys=1)
                jdata = r.json()
                self.data['mode'] = jdata["type"].upper().replace("CONTENTID", "PID")
                return jdata['source']
            except Exception as e:
                log.w('_get_ace_url error: {0}'.format(uni(e)))

    def _get_nox_url(self):
        nox_ip = defines.ADDON.getSetting('nox_ip')
        nox_port = str2int(defines.ADDON.getSetting('nox_port'))
        for server in _servers:
            try:
                params = dict(
                    session=self.session,
                    channel_id=self.id(),
                    typeresult='json')
                r = defines.request("http://{server}/v3/get_noxbit_cid.php".format(server=server), params=params, trys=1)

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

    def update_epglist(self):
        if not self.get('epg'):
            for server in _servers:
                try:
                    params = dict(
                        session=self.session,
                        epg_id=self.get('epg_id'),
                        typeresult='json')
                    r = defines.request('http://{server}/v3/translation_epg.php'.format(server=server),
                                        params=params, trys=1)

                    jdata = r.json()
                    if str2int(jdata.get('success')) != 0:
                        self.data['epg'] = jdata['data']
                        screens = self._get_screenshots()
                        if screens:
                            self.data['epg']['screens'] = screens
                        break
                except Exception as e:
                    log.d('update_epglist error: {0}'.format(uni(e)))

    def logo(self):
        name = self.name().lower()
        logo = os.path.join(self.yatv_logo_path, "{name}.png".format(name=name))
        if os.path.exists(logo):
            self.data['logo'] = logo

        try:
            if self.get('logo') and not os.path.exists(logo):
                ttv_logo = 'http://{server}/uploads/{logo}'.format(server='ttv.world', logo=uni(self.data['logo']))
                r = defines.request(ttv_logo)
                if len(r.content) > 0:
                    with open(logo, 'wb') as fp:
                        fp.write(r.content)
                self.data['logo'] = logo

        except Exception as e:
            log.e('update_logo error {0}'.format(e))

        if not self.get('logo'):
            self.data['logo'] = TChannel.logo(self)

        return self.get('logo')

    def _get_screenshots(self):
        for server in _servers:
            try:
                params = dict(
                    session=self.session,
                    channel_id=self.id(),
                    count=2,
                    typeresult='json')
                r = defines.request('http://{server}/v3/translation_screen.php'.format(server=server),
                                    params=params, trys=1)

                jdata = r.json()
                if str2int(jdata.get('success')) != 0 and not jdata.get('error'):
                    return [x['filename'] for x in jdata['screens']]
            except Exception as e:
                log.w('get_screenshots error: {0}'.format(uni(e)))


class Channels(TChannels):

    def __init__(self, prior=0):
        self.user = {}
        self.session = None
        TChannels.__init__(self, reload_interval=-1, prior=prior)

    def _initTTV(self):
        try:
            log.info("init TTV")
            guid = uni(defines.ADDON.getSetting("uuid"))
            if guid == '':
                guid = str(uuid.uuid1())
                defines.ADDON.setSetting("uuid", str2(guid))
            guid = guid.replace('-', '')

#             for server in _servers:
#                 try:
#                     params = dict(application='xbmc', version=defines.TTV_VERSION)
#                     r = defines.request(fmt('http://{server}/v3/version.php', server=server),
#                                         params=params, trys=1)
#                     jdata = r.json()
#                     if utils.str2int(jdata.get('success')) == 0:
#                         raise Exception(fmt("Check version error: {0}", jdata.get('error')))
#                     break
#                 except Exception as e:
#                     log.e(e)

            for server in _servers:
                try:
                    params = dict(
                        username=uni(defines.ADDON.getSetting('login')),
                        password=uni(defines.ADDON.getSetting('password')),
                        typeresult='json',
                        application='xbmc',
                        guid=guid
                    )
                    r = defines.request('http://{server}/v3/auth.php'.format(server=server),
                                        params=params, trys=1)
                    jdata = r.json()
                    if str2int(jdata.get('success')) == 0:
                        raise Exception("Auth error: {0}".format(uni(jdata.get('error'))))
                    break
                except Exception as e:
                    log.e(e)

            self.user = {"login": uni(defines.ADDON.getSetting('login')),
                         "balance": jdata.get("balance"),
                         "vip": jdata["balance"] > 1}

            self.session = jdata.get('session')
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
        if self.session:
            for server in _servers:
                try:
                    params = dict(
                        session=self.session,
                        type='channel',
                        typeresult='json')
                    r = defines.request('http://{server}/v3/translation_list.php'.format(server=server),
                                        params=params, trys=1)

                    jdata = r.json()

                    if str2int(jdata.get('success')) == 0:
                        raise Exception(jdata.get('error'))
                    break
                except Exception as e:
                    log.e('get_channels error: {0}'.format(uni(e)))

            if jdata.get('channels'):
                for ch in jdata['channels']:
                    try:
                        if not (ch.get("name") or ch.get("id")):
                            continue
                        channel = ch
                        channel['cat'] = self._get_groupname_by_id(jdata.get("categories"), ch['group'])
                        self.channels.append(Channel(channel, self.session))
                    except Exception as e:
                        log.e('Add channel error: {0}'.format(uni(e)))

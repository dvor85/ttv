# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from tchannel import TChannel, TChannels
import defines
import utils
import logger
import uuid

fmt = utils.fmt
log = logger.Logger(__name__)
_servers = ['api.torrent-tv.ru', '1ttvxbmc.top']


class TTVChannel(TChannel):

    def __init__(self, data={}, session=None):
        TChannel.__init__(self, data)
        self.data['players'] = ['ace', 'nox']
        self.session = session

    def get_url(self, player=None):
        if player == 'nox':
            return self._get_nox_url()
        else:
            return self._get_ace_url()

    def _get_ace_url(self):
        for server in _servers:
            try:
                params = dict(
                    session=self.session,
                    channel_id=self.get_id(),
                    typeresult='json')

                r = defines.request(fmt("http://{server}/v3/translation_stream.php", server=server),
                                    params=params, trys=1)
                jdata = r.json()
                self.data['url'] = jdata['source']
                self.data['mode'] = jdata["type"].upper().replace("CONTENTID", "PID")
                return self.data['url']
            except Exception as e:
                log.w(fmt('_get_ace_url error: {0}', e))

    def _get_nox_url(self):
        nox_ip = defines.ADDON.getSetting('nox_ip')
        nox_port = utils.str2int(defines.ADDON.getSetting('nox_port'))
        for server in _servers:
            try:
                params = dict(
                    session=self.session,
                    channel_id=self.get_id(),
                    typeresult='json')
                r = defines.request(fmt("http://{server}/v3/get_noxbit_cid.php", server=server), params=params, trys=1)

                jdata = r.json()
                if not jdata["success"]:
                    return
                if jdata["success"] == 0:
                    return
                cid = jdata["cid"]
                streamtype = defines.ADDON.getSetting('nox_streamtype')
                self.data['url'] = fmt("http://{nox_ip}:{nox_port}/{streamtype}?cid={cid}",
                                       nox_ip=nox_ip,
                                       nox_port=nox_port,
                                       streamtype=streamtype, cid=cid)
                return self.data['url']
            except Exception as e:
                log.w(fmt('_get_nox_url error: {0}', e))

    def update_epglist(self):
        if not self.data.get('epg'):
            for server in _servers:
                try:
                    params = dict(
                        session=self.session,
                        epg_id=self.data['epg_id'],
                        typeresult='json')
                    r = defines.request(fmt('http://{server}/v3/translation_epg.php', server=server),
                                        params=params, trys=1)

                    jdata = r.json()
                    if utils.str2int(jdata.get('success')) != 0:
                        self.data['epg'] = jdata['data']
                        break
                except Exception as e:
                    log.d(fmt('update_epglist error: {0}', e))

    def get_screenshots(self):
        for server in _servers:
            try:
                params = dict(
                    session=self.session,
                    channel_id=self.get_id(),
                    count=2,
                    typeresult='json')
                r = defines.request(fmt('http://{server}/v3/translation_screen.php', server=server),
                                    params=params, trys=1)

                jdata = r.json()

                if utils.str2int(jdata.get('success')) != 0:
                    return jdata['screens']
            except Exception as e:
                log.w(fmt('get_screenshots error: {0}', e))


class TTV(TChannels):

    def __init__(self):
        self.user = {}
        self.session = None
        TChannels.__init__(self)

    def _initTTV(self):
        try:
            log.info("init TTV")
            guid = defines.ADDON.getSetting("uuid")
            if guid == '':
                guid = str(uuid.uuid1())
                defines.ADDON.setSetting("uuid", guid)
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
                        username=defines.ADDON.getSetting('login'),
                        password=defines.ADDON.getSetting('password'),
                        typeresult='json',
                        application='xbmc',
                        guid=guid
                    )
                    r = defines.request(fmt('http://{server}/v3/auth.php', server=server),
                                        params=params, trys=1)
                    jdata = r.json()
                    if utils.str2int(jdata.get('success')) == 0:
                        raise Exception(fmt("Auth error: {0}", jdata.get('error')))
                    break
                except Exception as e:
                    log.e(e)

            self.user = {"login": defines.ADDON.getSetting('login'),
                         "balance": jdata.get("balance"),
                         "vip": jdata["balance"] > 1}

            self.session = jdata.get('session')
        except Exception as e:
            log.error(fmt("_initTTV error: {0}", e))

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
                    r = defines.request(fmt('http://{server}/v3/translation_list.php', server=server),
                                        params=params, trys=1)

                    jdata = r.json()

                    if utils.str2int(jdata.get('success')) == 0:
                        raise Exception(jdata.get('error'))
                    break
                except Exception as e:
                    log.e(fmt('get_channels error: {0}', e))

            if jdata.get('channels'):
                for ch in jdata['channels']:
                    try:
                        if not (ch.get("name") or ch.get("id")):
                            continue
                        channel = ch
                        channel['cat'] = self._get_groupname_by_id(jdata.get("categories"), ch['group'])
                        self.channels.append(TTVChannel(channel, self.session))
                    except Exception as e:
                        log.e(fmt('Add channel error: {0}', e))

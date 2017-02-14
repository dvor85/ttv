# -*- coding: utf-8 -*-

from interface import Channel
import defines
import utils
import logger
import re
import datetime
import uuid

fmt = utils.fmt
log = logger.Logger(__name__)
_re_url_match = re.compile('^(?:https?|ftps?|file)://')


class TTVChannel(Channel):

    def __init__(self, data={}, session=None):
        Channel.__init__(self, data)
        self.session = session

    def get_logo(self):
        if self.data.get('logo'):
            if not _re_url_match.search(self.data['logo']):
                return fmt('http://{0}/uploads/{1}', defines.SITE_MIRROR, self.data['logo'])
        return Channel.get_logo(self)

    def onStart(self):
        try:
            params = dict(
                session=self.session,
                channel_id=self.get_id(),
                typeresult='json')
            r = defines.request(fmt("http://{url}/v3/translation_stream.php", url=defines.API_MIRROR),
                                params=params)
            jdata = r.json()
            self.data['url'] = jdata['source']
            self.data['mode'] = jdata["type"].upper().replace("CONTENTID", "PID")
            return jdata
        except Exception as e:
            log.w(fmt('get_from_api error: {0}', e))

    def update_epglist(self):
        try:
            params = dict(
                session=self.session,
                epg_id=self.data['epg_id'],
                typeresult='json')
            r = defines.request(fmt('http://{url}/v3/translation_epg.php', url=defines.API_MIRROR),
                                params=params)

            jdata = r.json()
            if utils.str2int(jdata.get('success')) != 0:
                self.data['epg'] = jdata['data']

        except Exception as e:
            log.d(fmt('update_epglist error: {0}', e))

    def get_epg(self):
        try:
            ctime = datetime.datetime.now()
            dt = (ctime - datetime.datetime.utcnow()) - datetime.timedelta(hours=3)  # @UnusedVariable

            prev_bt = 0
            prev_et = 0
            curepg = []
            for x in self.data.get('epg', []):
                bt = datetime.datetime.fromtimestamp(float(x['btime']))
                et = datetime.datetime.fromtimestamp(float(x['etime']))
                if et > ctime and abs((bt.date() - ctime.date()).days) <= 1 and prev_et <= float(x['btime']) > prev_bt:
                    curepg.append(x)
                    prev_bt = float(x['btime'])
                    prev_et = float(x['etime'])
            return curepg

        except Exception as e:
            log.e(fmt('get_epg error {0}', e))

    def get_id(self):
        return fmt("{0}", Channel.get_id(self))


class TTV():

    def __init__(self):
        self.channels = []
        try:
            params = dict(application='xbmc', version=defines.TTV_VERSION)
            r = defines.request(fmt('http://{url}/v3/version.php', url=defines.API_MIRROR),
                                params=params)
            jdata = r.json()
            if utils.str2int(jdata.get('success')) == 0:
                raise Exception(jdata.get('error'))
        except Exception as e:
            log.e(fmt('onInit error: {0}', e))
            return
        if utils.str2int(jdata['support']) == 0:
            return

        guid = defines.ADDON.getSetting("uuid")
        if guid == '':
            guid = str(uuid.uuid1())
            defines.ADDON.setSetting("uuid", guid)
        guid = guid.replace('-', '')

        try:
            params = dict(
                username=defines.ADDON.getSetting('login'),
                password=defines.ADDON.getSetting('password'),
                typeresult='json',
                application='xbmc',
                guid=guid
            )
            r = defines.request(fmt('http://{url}/v3/auth.php', url=defines.API_MIRROR),
                                params=params)
            jdata = r.json()
            if utils.str2int(jdata.get('success')) == 0:
                log.e(Exception(fmt("Auth error: ", jdata.get('error'))))
        except Exception as e:
            log.e(fmt('onInit error: {0}', e))
            return

        self.user = {"login": defines.ADDON.getSetting('login'),
                     "balance": jdata["balance"],
                     "vip": jdata["balance"] > 1}

        self.session = jdata['session']

    def get_channels(self):
        params = dict(
            session=self.session,
            type='channel',
            typeresult='json')
        r = defines.request(fmt('http://{url}/v3/translation_list.php', url=defines.API_MIRROR),
                            params=params)

        jdata = r.json()

        if utils.str2int(jdata.get('success')) == 0:
            raise Exception(jdata.get('error'))

        if jdata.get('channels'):
            for ch in jdata['channels']:

                if not (ch.get("name") or ch.get("id")):
                    continue

                channel = {}
                groups = jdata.get("categories")
                if groups:
                    for g in groups:
                        if g['id'] == ch['group']:
                            channel['cat'] = g["name"]
                            break
                channel.update(ch)
                self.channels.append(TTVChannel(channel, self.session))
        return self.channels

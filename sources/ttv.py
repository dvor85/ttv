# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import defines
import time
import json
from utils import str2int
import requests
import logger
import uuid
from pathlib import Path
from .tchannel import TChannel, TChannels

log = logger.Logger(__name__)
_server = 'ttv.run'
_sess = requests.Session()


class Channel(TChannel):

    def __init__(self, data={}, ttv_session=None):
        TChannel.__init__(self, data=data, src='ttv', player='ace,nox,tsp')
        self.use_nox = defines.ADDON.getSettingBool('use_nox')
        self.use_ace = defines.ADDON.getSettingBool('use_ace')
        self.use_tsproxy = defines.ADDON.getSettingBool('use_tsproxy')
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

            r = defines.request(f"http://api.{_server}/v3/translation_stream.php", params=params, session=_sess, trys=1)
            jdata = r.json()
            if not jdata["success"]:
                return

            self.data['mode'] = jdata["type"].upper().replace("CONTENTID", "PID")
            return jdata['source']
        except Exception as e:
            log.w(f'_get_ace_url error: {e}')

    def _get_nox_url(self):
        nox_ip = defines.ADDON.getSetting('nox_ip')
        nox_port = defines.ADDON.getSettingInt('nox_port')
        try:
            params = dict(
                session=self.ttv_session,
                channel_id=self.id(),
                typeresult='json')
            r = defines.request(f"http://api.{_server}/v3/get_noxbit_cid.php", params=params, session=_sess, trys=1)

            jdata = r.json()
            if not jdata["success"]:
                return

            cid = jdata["cid"]
            streamtype = defines.ADDON.getSetting('nox_streamtype')
            return f"http://{nox_ip}:{nox_port}/{streamtype}?cid={cid}"
        except Exception as e:
            log.w(f'_get_nox_url error: {e}')

    def _get_tsproxy_url(self):
        zoneid = 0
        nohls = int(not defines.ADDON.getSettingBool("proxy_hls"))
        try:
            params = dict(
                session=self.ttv_session,
                channel_id=self.id(),
                typeresult='json',
                zone_id=zoneid,
                nohls=nohls)
            r = defines.request(f"http://api.{_server}/v3/translation_http.php", params=params, session=_sess, trys=1)

            jdata = r.json()
            if not jdata["success"]:
                return

            if jdata['source'].endswith('.m3u8'):
                with defines.progress_dialog(f'Ожидание источника для канала: {self.title()}.') as pd:
                    for t in range(5):
                        if pd.iscanceled() or defines.isCancel():
                            break
                        r = defines.request(jdata['source'], session=_sess, trys=2, interval=2)
                        if r.ok:
                            srcs = [s for s in r.text.splitlines() if s.startswith('http') and 'errors' not in s]
                            if len(srcs) > 2:
                                break
                        for k in range(5):
                            defines.monitor.waitForAbort(1.2)
                            pd.update(4 * (5 * t + k + 1))

            return jdata['source']
        except Exception as e:
            log.w(f'_get_tsproxy_url error: {e}')

    def update_epglist(self):
        defines.MyThread(TChannel.update_epglist, self).start().join(4)
        if not self.get('epg'):
            try:
                params = dict(
                    session=self.ttv_session,
                    epg_id=self.get('epg_id'),
                    typeresult='json')
                r = defines.request(f'http://api.{_server}/v3/translation_epg.php', params=params, session=_sess, trys=1)

                jdata = r.json()
                if str2int(jdata.get('success')) != 0:
                    self.data['epg'] = jdata['data']
            except Exception as e:
                log.d(f'update_epglist error: {e}')

    def logo(self, *args):
        if self.get('logo') and '://' not in self.get('logo'):
            self.data['logo'] = f"http://vvv.{_server}/uploads/{self.get('logo')}"
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
        r = defines.request(f'http://api.{_server}/v3/translation_screen.php', params=params, session=_sess, trys=1)
        if r.ok:
            jdata = r.json()
            if str2int(jdata.get('success')) != 0 and not jdata.get('error'):
                info['screens'] = [x['filename'].replace('web1.1ttv.org', f'shot.{_server}') for x in jdata['screens']]

        return info


class Channels(TChannels):

    def __init__(self):
        self.user = {}
        self.ttv_session = None
        self._temp = Path(defines.CACHE_PATH, "ttv.json")
        TChannels.__init__(self, name='ttv', reload_interval=3600)

    def _load_jdata(self, avail=True):
        log.d(f'get {self._temp}')
        if self._temp.exists():
            if not avail or (time.time() - self._temp.stat().st_mtime <= self.reload_interval):
                with self._temp.open(mode='r') as fp:
                    return json.load(fp)
        else:
            log.w(f"{self._temp} not exists")

    def _save_jdata(self, jdata):
        with self._temp.open(mode='w+') as fp:
            json.dump(jdata, fp)

    def _initTTV(self):
        try:
            log.info("init TTV")
            guid = defines.ADDON.getSetting("uuid")
            if guid == '':
                guid = str(uuid.uuid1())
                defines.ADDON.setSetting("uuid", guid)
            guid = guid.replace('-', '')

            try:
                params = dict(
                    username=defines.ADDON.getSetting('ttv_login'),
                    password=defines.ADDON.getSetting('ttv_password'),
                    typeresult='json',
                    application='xbmc',
                    guid=guid
                )
                r = defines.request(f'http://api.{_server}/v3/auth.php', params=params, session=_sess, trys=1)
                jdata = r.json()
                if str2int(jdata.get('success')) == 0:
                    raise Exception(f"Auth error: {jdata.get('error')}")
            except Exception as e:
                log.e(e)

            self.user = {"login": defines.ADDON.getSetting('ttv_login'),
                         "balance": jdata.get("balance"),
                         "vip": jdata["balance"] > 1}

            self.ttv_session = jdata.get('session')
        except Exception as e:
            log.error(f"_initTTV error: {e}")

    def _get_groupname_by_id(self, categories, chid):
        if categories:
            return next((g.get("name") for g in categories if g.get('id') == chid), None)

    def update_channels(self):
        self._initTTV()
        jdata = {}
        try:
            jdata = self._load_jdata()
            if not jdata:
                if self.ttv_session:
                    params = dict(
                        session=self.ttv_session,
                        type='channel',
                        typeresult='json')
                    r = defines.request(f'http://api.{_server}/v3/translation_list.php', params=params, session=_sess, trys=1)
                    if r.ok:
                        jdata = r.json()

                        if str2int(jdata.get('success')) == 0:
                            log.e(jdata.get('error'))
                            return
                        else:
                            self._save_jdata(jdata)
        except Exception as e:
            log.e(f'get_channels error: {e}')

        if jdata and jdata.get('channels'):
            for ch in jdata['channels']:
                try:
                    if ch.get("name") or ch.get("id"):
                        ch.setdefault('cat', self._get_groupname_by_id(jdata.get("categories"), ch['group']))
                        self.channels.append(Channel(ch, self.ttv_session))
                except Exception as e:
                    log.e(f'Add channel error: {e}')

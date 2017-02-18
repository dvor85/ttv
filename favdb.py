# -*- coding: utf-8 -*-
# Writer (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import os
import defines
import logger
import json
import xbmc
import utils


log = logger.Logger('FDB')
fmt = utils.fmt


class FDB():
    API_ERROR_INCORRECT = 'incorrect'
    API_ERROR_NOCONNECT = 'noconnect'
    API_ERROR_ALREADY = 'already'
    API_ERROR_NOPARAM = 'noparam'
    API_ERROR_NOFAVOURITE = 'nofavourite'

    def __init__(self):
        self.channels = []

    def get(self):
        pass

    def add(self, ch):
        pass

    def save(self):
        pass

    def get_json(self):
        pass

    def delete(self, name):
        log.d(fmt('delete channel name={0}', name))
        k = self.find(name)
        if k is not None:
            if not self.channels:
                self.get()
            if self.channels:
                del(self.channels[k])
                return self.save()
        return FDB.API_ERROR_NOFAVOURITE

    def moveTo(self, name, to_id):
        to_id -= 1
        name = utils.utf(name).lower()
        if not self.channels:
            self.get()
        if self.channels and to_id < len(self.channels):
            k = self.find(name)
            log.d(fmt('moveTo channel from {0} to {1}', k, to_id))
            return self.swapTo(k, to_id)

        return FDB.API_ERROR_NOPARAM

    def find(self, name):
        name = utils.utf(name).lower()
        log.d(fmt('find channel by name={0}', name))
        if not self.channels:
            self.get()
        if self.channels:
            for i, ch in enumerate(self.channels):
                if utils.utf(ch['name']).lower() == name:
                    return i

    def swap(self, i1, i2):
        log.d(fmt('swap channels with indexes={0},{1}', i1, i2))
        try:
            ch = self.channels[i1]
            self.channels[i1] = self.channels[i2]
            self.channels[i2] = ch
        except Exception as e:
            log.w(e)
            return
        return True

    def swapTo(self, from_id, to_id):
        sign = cmp(to_id - from_id, 0)
        for i in range(from_id, to_id, sign):
            if not self.swap(i, i + sign):
                break
        return self.save()

    def down(self, name):
        to_id = self.find(name) + 1
        return self.moveTo(name, to_id + 1)

    def up(self, name):
        to_id = self.find(name) + 1
        return self.moveTo(name, to_id - 1)


class LocalFDB(FDB):

    def __init__(self):
        FDB.__init__(self)
        log.d('init LocalFDB')
        self.DB = os.path.join(defines.DATA_PATH, 'favdb.json')

    def get(self):
        log.d('get channels')
        if os.path.exists(self.DB):
            with open(self.DB, 'r') as fp:
                try:
                    self.channels = json.load(fp)
                except Exception as e:
                    log.w(fmt('get error: {0}', e))
        return self.channels

#     def get_json(self):
#         if not self.channels:
#             self.get()
#         if self.channels:
#             return {'channels': self.channels, 'success': 1}
#         else:
#             return {'channels': [], 'success': 0, 'error': 'Error loading local channels'}

    def save(self, obj=None):
        log.d('save channels')
        try:
            with open(self.DB, 'w+') as fp:
                if not obj:
                    obj = self.channels
                json.dump(obj, fp)
                self.channels = obj
                return True
        except Exception as e:
            log.w(fmt('save error: {0}', e))
            return FDB.API_ERROR_NOCONNECT

    def add(self, ch):
        name = ch.get_name()
        log.d(fmt('add channels {0}', name))
        channel = {'name': name,
                   'cat': ch.get('cat'),
                   }

        if self.find(name) is None:
            self.channels.append(channel)
            return self.save()

        return FDB.API_ERROR_ALREADY


class RemoteFDB(FDB):

    def __init__(self, session):
        FDB.__init__(self)
        log.d('init RemoteFDB')
        self.session = session
        self.cookie = []

    def get(self):
        try:
            jdata = self.get_json()
            if utils.str2int(jdata['success']) != 0:
                channels = jdata['channels']
                self.channels = []
                for i, ch in enumerate(channels):
                    chdata = {'id': ch['id'], 'pos': i}
                    self.channels.append(chdata)
        except Exception as e:
            log.e(fmt('get error: {0}', e))
        return self.channels

    def get_json(self):
        try:
            params = dict(
                session=self.session,
                type='favourite',
                typeresult='json')
            r = defines.request(fmt('http://{url}/v3/translation_list.php', url=defines.API_MIRROR),
                                params=params)
            r.raise_for_status()

            jdata = r.json()
            return jdata
        except Exception as e:
            log.e(fmt('get_json error: {0}', e))

    def add(self, li):
        chid = utils.str2int(li.getProperty('id'))
        log.d(fmt('add channels {0}', chid))

        if self.find(chid) is None:
            channel = {'id': chid,
                       'pos': len(self.channels)}
            self.channels.append(channel)
            return self.save()

        return FDB.API_ERROR_ALREADY

    def swap(self, i1, i2):
        log.d(fmt('swap channels with indexes={0},{1}', i1, i2))
        try:
            chid = self.channels[i1]['id']
            self.channels[i1]['id'] = self.channels[i2]['id']
            self.channels[i2]['id'] = chid
        except Exception as e:
            log.w(e)
            return
        return True

    def __exec_cmd(self, li, cmd):
        log.d('exec_cmd')
        try:
            params = dict(
                session=self.session,
                channel_id=li.getProperty('id'),
                typeresult='json')
            r = defines.request(fmt('http://{url}/v3/{cmd}.php', url=defines.API_MIRROR, cmd=cmd),
                                params=params)
            r.raise_for_status()
            jdata = r.json()

            if utils.str2int(jdata['success']) == 0:
                return jdata.get('error')
        except Exception as e:
            msg = fmt('exec_cmd error: {0}', e)
            log.e(msg)
            return FDB.API_ERROR_NOCONNECT
        return True

    def down(self, li):
        return self.__exec_cmd(li, 'favourite_down')

    def up(self, li):
        return self.__exec_cmd(li, 'favourite_up')

    def delete(self, li):
        return self.__exec_cmd(li, 'favourite_delete')

    def __post_to_site(self, target, jdata):
        try:
            import urllib
            import urllib2
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) \
                                      Chrome/45.0.2454.99 Safari/537.36',
                       'Content-type': 'application/x-www-form-urlencoded',
                       'Accept-Encoding': 'gzip, deflate',
                       }

            if len(self.cookie) == 0:
                req = urllib2.Request(fmt('http://{0}/banhammer/pid', defines.SITE_MIRROR), headers=headers)
                resp = urllib2.urlopen(req, timeout=6)
                try:
                    self.cookie.append(fmt('BHC={0}; path=/;', resp.headers['X-BH-Token']))
                finally:
                    resp.close()

                authdata = {
                    'email': defines.ADDON.getSetting('login'),
                    'password': defines.ADDON.getSetting('password'),
                    'remember': 1,
                    'enter': 'enter'
                }
                req = urllib2.Request(
                    fmt('http://{0}/auth.php', defines.SITE_MIRROR), data=urllib.urlencode(authdata), headers=headers)
                for cookie in self.cookie:
                    req.add_header('Cookie', cookie)
                resp = urllib2.urlopen(req, timeout=6)
                try:
                    for h in resp.headers.headers:
                        keyval = h.split(':')
                        if 'Set-Cookie' in keyval[0]:
                            self.cookie.append(keyval[1].strip())
                finally:
                    resp.close()

            headers.pop('Accept-Encoding')
            req = urllib2.Request(target, data=fmt('ch={0}', urllib2.quote(jdata)), headers=headers)
            for cookie in self.cookie:
                req.add_header('Cookie', cookie)
            resp = urllib2.urlopen(req, timeout=6)
            try:
                return resp.read()
            finally:
                resp.close()
        except Exception as e:
            self.cookie = []
            log.e(fmt('ERROR: {0} on post query to {1}', e, target))

    def save(self):
        if self.channels:
            jdata = json.dumps(self.channels)
            for i in range(10):
                log.d(fmt('try to save: {0}', i))
                data = self.__post_to_site(fmt('http://{0}/store_sorted.php', defines.SITE_MIRROR), jdata)
                try:
                    jdata = json.loads(data)
                    if utils.str2int(jdata['success']) == 1:
                        return True

                except Exception as e:
                    log.e(fmt('save error: {0}', e))
                    self.cookie = []
                    if not defines.isCancel():
                        xbmc.sleep(900)
                    else:
                        break

            self.channels = None
            return FDB.API_ERROR_NOCONNECT

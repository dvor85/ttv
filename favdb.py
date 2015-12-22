  # -*- coding: utf-8 -*-
# Writer (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import os
import defines
import json
import xbmc

log = defines.Logger('FDB')

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
    
    
    def add(self, li):
        pass
    
    
    def save(self):
        pass
    
    
    def delete(self, li):
        chid = int(li.getProperty('id'))
        log.d('delete channel id={0}'.format(chid))
        k = self.find(chid)
        if not k is None:            
            if not self.channels:
                self.get()
            if self.channels:
                del(self.channels[k])
                return self.save()
        return FDB.API_ERROR_NOFAVOURITE
            
    
    def moveTo(self, li, to_id):
        to_id -= 1
        chid = int(li.getProperty('id'))        
        if not self.channels:
            self.get()
        if self.channels and to_id < len(self.channels):
            k = self.find(chid)
            log.d('moveTo channel from {0} to {1}'.format(k, to_id))
            return self.swapTo(k, to_id)
        
        return FDB.API_ERROR_NOPARAM
        
    
    def find(self, chid):
        log.d('find channel by id={0}'.format(chid))
        if not self.channels:
            self.get()
        if self.channels:
            for i, ch in enumerate(self.channels):
                if ch['id'] == chid:
                    return i
                
                
    def swap(self, i1, i2):
        log.d('swap channels with indexes={0},{1}'.format(i1, i2))
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
    
    
    def down(self, li):
        chid = int(li.getProperty('id'))
        to_id = self.find(chid) + 1   
        return self.moveTo(li, to_id + 1)
        
    
    def up(self, li):
        chid = int(li.getProperty('id'))  
        to_id = self.find(chid) + 1 
        return self.moveTo(li, to_id - 1)
    


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
                    log.w('get error: {0}'.format(e))
        return self.channels
            
                    
                
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
            log.w('save error: {0}'.format(e))
            return FDB.API_ERROR_NOCONNECT
            
    
    def add(self, li):
        chid = int(li.getProperty('id'))
        log.d('add channels {0}'.format(chid))
        channel = {'id': chid,
                   'type': li.getProperty('type'),
                   'logo': os.path.basename(li.getProperty('icon')),
                   'access_translation': li.getProperty('access_translation'),
                   'access_user': int(li.getProperty('access_user')),
                   'name': li.getProperty('name'),
                   'epg_id': int(li.getProperty('epg_cdn_id'))}
        if self.find(chid) is None:
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
            data = defines.GET('http://{0}/v3/translation_list.php?session={1}&type={2}&typeresult=json'.format(defines.API_MIRROR, self.session, 'favourite'), cookie=self.session, trys=10)
            jdata = json.loads(data)
            if jdata['success'] != 0:
                channels = jdata['channels']
                self.channels = []
                for i, ch in enumerate(channels):
                    chdata = {'id': ch['id'], 'pos': i}
                    self.channels.append(chdata)
        except Exception as e:
            log.e('get error: {0}'.format(e))
        return self.channels
        
        
    def add(self, li):
        chid = int(li.getProperty('id'))
        log.d('add channels {0}'.format(chid))
          
        if self.find(chid) is None:
            channel = {'id': chid,
                       'pos': len(self.channels)} 
            self.channels.append(channel)
            return self.save()

        return FDB.API_ERROR_ALREADY
    
        
    def swap(self, i1, i2):
        log.d('swap channels with indexes={0},{1}'.format(i1, i2))
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
            channel_id = li.getProperty('id')
            data = defines.GET('http://{0}/v3/{1}.php?session={2}&channel_id={3}&typeresult=json'.format(defines.API_MIRROR, self.session, channel_id), cookie=self.session, trys=10)
            jdata = json.loads(data)
            if jdata['success'] == 0:
                return jdata['error']
        except Exception as e:
            msg = 'exec_cmd error: {0}'.format(e)
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
            import urllib, urllib2
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.99 Safari/537.36',
                       'Content-type': 'application/x-www-form-urlencoded',
                       'Accept-Encoding': 'gzip, deflate',
            }
            
            if len(self.cookie) == 0:
                req = urllib2.Request('http://torrent-tv.ru/banhammer/pid', headers=headers)
                resp = urllib2.urlopen(req, timeout=6)
                try:
                    self.cookie.append('BHC={0}; path=/;'.format(resp.headers['X-BH-Token']))
                finally:
                    resp.close()
                
                authdata = {
                    'email' : defines.ADDON.getSetting('login'),
                    'password' : defines.ADDON.getSetting('password'),
                    'remember' : 1,
                    'enter' : 'enter'
                }
                req = urllib2.Request('http://torrent-tv.ru/auth.php', data=urllib.urlencode(authdata), headers=headers)
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
                # self.cookie.append(resp.headers['Set-Cookie'].split(";")[0])
            
            headers.pop('Accept-Encoding')
            req = urllib2.Request(target, data='ch={0}'.format(urllib2.quote(jdata)), headers=headers)
            for cookie in self.cookie:
                req.add_header('Cookie', cookie)
            resp = urllib2.urlopen(req, timeout=6)
            try:
                return resp.read()
            finally:
                resp.close()
        except Exception as e:
            self.cookie = []
            log.e('ERROR: {0} on post query to {1}'.format(e, target))
            
    
    def save(self):
        if self.channels:
            jdata = json.dumps(self.channels)
            for i in range(10):
                log.d('try to save: {0}'.format(i))
                data = self.__post_to_site('http://torrent-tv.ru/store_sorted.php', jdata)
                try:
                    jdata = json.loads(data)
                    if int(jdata['success']) == 1:
                        return True
                    
                except Exception as e:
                    log.e('save error: {0}'.format(e))
                    self.cookie = []
                    if not defines.isCancel():
                        xbmc.sleep(900)
                    else:
                        break
            
            self.channels = None
            return FDB.API_ERROR_NOCONNECT
 
        

  # -*- coding: utf-8 -*-
# Writer (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import os
import defines
import json

log = defines.Logger('FDB')

class FDB():
    
    def __init__(self):
        self.channels = None
        
    def get(self):
        pass
    
    def add(self, li):
        pass
    
    def save(self):
        pass
    
    def delete(self, li):
        chid = int(li.getProperty('id'))
        log.d(u'delete channel id={0}'.format(chid))
        k = self.find(chid)
        if not k is None:            
            if not self.channels:
                self.get()
            if self.channels:
                del(self.channels[k])
                return self.save()
    
    def moveTo(self, li, to_id):
        to_id -= 1
        chid = int(li.getProperty('id'))        
        if not self.channels:
            self.get()
        if self.channels and to_id < len(self.channels):
            k = self.find(chid)
            log.d(u'moveTo channel from {0} to {1}'.format(k, to_id))
            return self.swapTo(k, to_id)
    
    def find(self, chid):
        log.d(u'find channel by id={0}'.format(chid))
        if not self.channels:
            self.get()
        if self.channels:
            for i, ch in enumerate(self.channels):
                if ch['id'] == chid:
                    return i
                
    def swap(self, i1, i2):
        log.d(u'swap channels with indexes={0},{1}'.format(i1, i2))
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
                    return self.channels
                except Exception as e:
                    log.w(u'get error: {0}'.format(e))
                
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
            log.w(u'save error: {0}'.format(e))
    
    def add(self, li):
        chid = int(li.getProperty('id'))
        log.d(u'add channels {0}'.format(chid))
        channel = {'id': chid,
                   'type': li.getProperty('type'),
                   'logo': os.path.basename(li.getProperty('icon')),
                   'access_translation': li.getProperty('access_translation'),
                   'access_user': int(li.getProperty('access_user')),
                   'name': li.getProperty('name'),
                   'epg_id': int(li.getProperty('epg_cdn_id'))}
        if not self.channels:
            self.get()
        if self.channels:
            if self.find(chid) is None:
                self.channels.append(channel)
                self.save()
            return True
    

            
class RemoteFDB(FDB):
    
    def __init__(self, session):
        FDB.__init__(self)
        log.d('init RemoteFDB')
        self.session = session
        self.cookie = []#defines.ADDON.getSetting('cookie')
        
    def add(self, li):
        chid = int(li.getProperty('id'))
        log.d(u'add channels {0}'.format(chid))
        if not self.channels:
            self.get()
        if self.channels:
            channel = {'id': chid,
                       'pos': len(self.channels)}
        
            if self.find(chid) is None:
                self.channels.append(channel)
                self.save()
            return True  
        
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

        
#     def __exec_cmd(self, li, cmd):
#         log.d('exec_cmd')
#         channel_id = li.getProperty('id')
#         data = defines.GET('http://api.torrent-tv.ru/v3/%s?session=%s&channel_id=%s&typeresult=json' % (cmd, self.session, channel_id), cookie=self.session)
#         try:
#             jdata = json.loads(data)
#         except Exception as e:
#             msg = u'exec_cmd error: {0}'.format(e)
#             log.e(msg)
#             return msg
#         if jdata['success'] == 0:
#             return jdata['error'].encode('utf-8')
#         return True
        
    def get(self):        
        data = defines.GET('http://api.torrent-tv.ru/v3/translation_list.php?session=%s&type=%s&typeresult=json' % (self.session, 'favourite'), cookie=self.session)
        try:
            jdata = json.loads(data)
            if jdata['success'] != 0:
                channels = jdata['channels']
                self.channels = []
                for i, ch in enumerate(channels):
                    chdata = {'id': ch['id'], 'pos': i}
                    self.channels.append(chdata)
        except Exception as e:
            log.e('get error: {0}'.format(e))
            return
        
    def __post_to_site(self, target, jdata):
        try:
            import urllib, urllib2
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.99 Safari/537.36',
                       'Content-type': 'application/x-www-form-urlencoded',
                       'Accept-Encoding': 'gzip, deflate',
            }
            
            if len(self.cookie) == 0:
                req = urllib2.Request('http://torrent-tv.ru/banhammer/pid', headers=headers)
                resp = urllib2.urlopen(req)
                self.cookie.append('BHC={0}; /auth.php;'.format(resp.headers['X-BH-Token'].split(";")[0]))
                
                authdata = {
                    'email' : defines.ADDON.getSetting('login'),
                    'password' : defines.ADDON.getSetting('password'),
                    'remember' : 1,
                    'enter' : 'enter'
                }
                req = urllib2.Request('http://torrent-tv.ru/auth.php', data=urllib.urlencode(authdata), headers=headers)
                for cookie in self.cookie:
                    req.add_header('Cookie', cookie)
                resp = urllib2.urlopen(req)
                self.cookie.append(resp.headers['Set-Cookie'].split(";")[0])
            
            headers.pop('Accept-Encoding')
            req = urllib2.Request(target, data='ch={0}'.format(urllib2.quote(jdata)), headers=headers)
            for cookie in self.cookie:
                req.add_header('Cookie', cookie)
            resp = urllib2.urlopen(req)
            return resp.read()
        except Exception as e:
            self.cookie = []
            log.e('ERROR: {0} on post query to {1}'.format(e, target))
            
    
    def save(self):
        if self.channels:
            jdata = json.dumps(self.channels)
            data = self.__post_to_site('http://torrent-tv.ru/store_sorted.php', jdata)
            try:
                jdata = json.loads(data)
                if int(jdata['success']) == 1:
                    return True
                
            except Exception as e:
                log.e('save error: {0}'.format(e))
 
        

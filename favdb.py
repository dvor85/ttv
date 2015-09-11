# -*- coding: utf-8 -*-
# Writer (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import os
import defines
import json

log = defines.Logger('FDB')

class FDB():
    
    def add(self, li):
        pass
    
    def delete(self, li):
        pass
    
    def up(self, li):
        pass
    
    def down(self, li):
        pass

class LocalFDB(FDB):

    def __init__(self):
        log.d('init LocalFDB')
        self.DB = os.path.join(defines.DATA_PATH, 'favdb.json')
        self.channels = None
        
    def get(self):
        log.d('get channels')
        if os.path.exists(self.DB):
            with open(self.DB, 'r') as fp:
                try:
                    self.channels = json.load(fp) 
                    return self.channels
                except Exception as e:
                    log.w('get error: {0}'.format(e))
                
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
        if not self.channels:
            self.get()
        if self.channels:
            if self.find(chid) is None:
                self.channels.append(channel)
                self.save()
            return True
    
    def find(self, chid):
        log.d('find channel by id={0}'.format(chid))
        if not self.channels:
            self.get()
        if self.channels:
            for i, ch in enumerate(self.channels):
                if ch['id'] == chid:
                    return i
            
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
        
    def swap(self, i1, i2):
        log.d('swap channels with indexes={0},{1}'.format(i1, i2))
        ch = self.channels[i1]
        self.channels[i1] = self.channels[i2]
        self.channels[i2] = ch
        return self.save()
        
    def up(self, li):
        chid = int(li.getProperty('id'))
        log.d('up channel with id={0}'.format(chid))
        if not self.channels:
            self.get()
        if self.channels:
            k = self.find(chid)
            if k > 0:
                return self.swap(k, k - 1)
            
    def down(self, li):
        chid = int(li.getProperty('id'))
        log.d('down channel with id={0}'.format(chid))
        if not self.channels:
            self.get()
        if self.channels:
            k = self.find(chid)
            if k < len(self.channels) - 1:
                return self.swap(k + 1, k)
            
class RemoteFDB(FDB):
    CMD_ADD_FAVOURITE = 'favourite_add.php'
    CMD_DEL_FAVOURITE = 'favourite_delete.php'
    CMD_UP_FAVOURITE = 'favourite_up.php'
    CMD_DOWN_FAVOURITE = 'favourite_down.php'
    
    def __init__(self, session):
        log.d('init RemoteFDB')
        self.session = session
        
    def exec_cmd(self, li, cmd):
        log.d('exec_cmd')
        channel_id = li.getProperty('id')
        data = defines.GET('http://api.torrent-tv.ru/v3/%s?session=%s&channel_id=%s&typeresult=json' % (cmd, self.session, channel_id), cookie=self.session)
        try:
            jdata = json.loads(data)
        except Exception as e:
            msg = 'Error load json object {0}'.format(e)
            log.e(msg)
            return 'Error load json object'
        if jdata['success'] == 0:
            return jdata['error'].encode('utf-8')
        return True
        
    def add(self, li):
        return self.exec_cmd(li, RemoteFDB.CMD_ADD_FAVOURITE)
    
    def delete(self, li):
        return self.exec_cmd(li, RemoteFDB.CMD_DEL_FAVOURITE)
        
    def up(self, li):
        return self.exec_cmd(li, RemoteFDB.CMD_UP_FAVOURITE)
            
    def down(self, li):
        return self.exec_cmd(li, RemoteFDB.CMD_DOWN_FAVOURITE)        
            
 
        

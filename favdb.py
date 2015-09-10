  # -*- coding: utf-8 -*-

import os
import defines
import json

log = defines.Logger('FavDB')

class FavDB(object):

    def __init__(self):
        log.d('init favDB')
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
        log.d('add channels')
        channel = {'id': int(li.getProperty('id')),
                   'type': li.getProperty('type'),
                   'logo': os.path.basename(li.getProperty('icon')),
                   'access_translation': li.getProperty('access_translation'),
                   'access_user': int(li.getProperty('access_user')),
                   'name': li.getProperty('name'),
                   'epg_id': int(li.getProperty('epg_cdn_id'))}
        if not self.channels:
            self.get()
        if self.channels:
            if self.find(channel['id']) is None:
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
            
    def delete(self, index):
        log.d('delete channel with index={0}'.format(index))
        if not self.channels:
            self.get()
        if self.channels:
            del(self.channels[index])
            return self.save()
        
    def swap(self, i1, i2):
        log.d('swap channels with indexes={0},{1}'.format(i1, i2))
        ch = self.channels[i1]
        self.channels[i1] = self.channels[i2]
        self.channels[i2] = ch
        return self.save()
        
    def up(self, li):
        log.d('up channel with id={0}'.format(li.getProperty('id')))
        if not self.channels:
            self.get()
        if self.channels:
            k = self.find(int(li.getProperty('id')))
            if k > 0:
                return self.swap(k, k - 1)
            
    def down(self, li):
        log.d('down channel with id={0}'.format(li.getProperty('id')))
        if not self.channels:
            self.get()
        if self.channels:
            k = self.find(int(li.getProperty('id')))
            if k < len(self.channels) - 1:
                return self.swap(k + 1, k)
             
                
                
            
 
        

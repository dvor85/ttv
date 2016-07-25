# -*- coding: utf-8 -*-
import os

class TChannels():

    def __init__(self, Channels):
        self.Channels = Channels
        self.tChannels = []
        
    def get(self): 
        if not self.tChannels:                
            for ch in self.Channels:
                channel = {'id': ch['url'][ch['url'].rfind('=')+1:],
                           'url': ch['url'],
                           'type': 'channel',
                           'logo': os.path.basename(ch['img']),
                           'access_translation': 1,
                           'access_user': 1,
                           'name': ch["title"].decode('utf-8', 'ignore')}
                channel['epg_id'] = "#%s" % channel['id']
                self.tChannels.append(channel)            
        return self.tChannels   
    
    def find(self, id):
        if not self.tChannels:
            self.get()
        for ch in self.tChannels:
            if ch['id'] == id:
                return ch

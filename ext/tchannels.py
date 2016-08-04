  # -*- coding: utf-8 -*-

class TChannels():

    def __init__(self, Channels):
        self.Channels = Channels
        self.tChannels = []
        
    def get(self): 
        if not self.tChannels:                
            for ch in self.Channels:
                if  ch['url'].rfind('=') > -1:
                    chid = ch['url'][ch['url'].rfind('=') + 1:]
                else:
                    chid = ch['title']
                channel = {'id': chid,
                           'url': ch['url'],
                           'type': 'channel',
                           'logo': ch['img'],
                           'access_translation': 1,
                           'access_user': 1,
                           'name': ch["title"].decode('utf-8', 'ignore')}
                channel['epg_id'] = "#%s" % channel['id']
                self.tChannels.append(channel)            
        return self.tChannels   
    
    def find_by_id(self, chid):
        if not self.tChannels:
            self.get()
        for ch in self.tChannels:
            if ch['id'] == chid:
                return ch
            
    def find_by_title(self, title):
        if not self.tChannels:
            self.get()
        for ch in self.tChannels:
            if ch['name'].lower().strip() == title.lower().strip():
                return ch

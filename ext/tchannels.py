# -*- coding: utf-8 -*-

import re


class TChannels():

    def __init__(self, Channels):
        self.Channels = Channels
        self.tChannels = []
        self._re_channel = re.compile('channel=(?P<chid>\d+)')

    def get(self):
        if not self.tChannels:
            for ch in self.Channels:
                title = ch["title"].decode('utf-8', 'ignore')
                m = self._re_channel.search(ch['url'])
                chid = m.group('chid') if m else title
                epg_id = 'channel=%s' % chid if m else 'title=%s' % chid

                channel = {'id': chid,
                           'url': ch['url'],
                           'type': 'channel',
                           'logo': ch['img'],
                           'access_user': 1,
                           'name': title,
                           'epg_id': epg_id}
                self.tChannels.append(channel)
        return self.tChannels

    def get_json(self):
        self.get()
        if self.tChannels:
            return {'channels': self.tChannels, 'success': 1}
        else:
            return {'channels': [], 'success': 0, 'error': 'Error by loading local ext channels'}

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

# -*- coding: utf-8 -*-

import re
import utils


class TChannels():

    def __init__(self, Channels):
        self.Channels = Channels
        self.tChannels = []
        self._re_channel = re.compile('channel=(?P<chid>\d+)')

    def get(self):
        if not self.tChannels:
            for ch in self.Channels:
                title = utils.utf(ch.get("title", ch.get('name', '')))
                m = self._re_channel.search(ch['url'])
                chid = m.group('chid') if m else title
                epg_id = 'channel=%s' % chid if m else 'title=%s' % chid

                channel = {'id': chid,
                           'url': ch['url'],
                           'type': 'channel',
                           'logo': ch.get('img', ''),
                           'access_user': 1,
                           'name': title,
                           'epg_id': epg_id,
                           'cat': ch.get('cat')}
                self.tChannels.append(channel)
        return self.tChannels

    def get_json(self):
        self.get()
        if self.tChannels:
            return {'channels': self.tChannels, 'success': 1}
        else:
            return {'channels': [], 'success': 0, 'error': 'Error by loading local sources channels'}

    def find_by_id(self, chid):
        if not self.tChannels:
            self.get()
        for ch in self.tChannels:
            if utils.utf(ch['id']) == utils.utf(chid):
                return ch

    def find_by_title(self, title):
        if not self.tChannels:
            self.get()
        for ch in self.tChannels:
            if utils.utf(ch['name']).lower().strip() == utils.utf(title).lower().strip():
                return ch

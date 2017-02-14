# -*- coding: utf-8 -*-

from UserDict import UserDict
import utils


class Channel(UserDict):

    def __init__(self, data={}):
        self.data = {}
        self.data['type'] = 'channel'
        self.data['cat'] = __name__
        self.data['mode'] = "PID"
        self.data.update(data)

    def onStart(self):
        pass

    def get_url(self):
        return self.data.get('url')

    def get_mode(self):
        return self.data.get('mode')

    def get_logo(self):
        return utils.true_enc(self.data.get('logo'))

    def get_id(self):
        return utils.utf(self.data.get('id'))

    def get_name(self):
        return utils.utf(self.data.get('name'))

    def update_epglist(self):
        return self.data.get('epg')

    def get_epg(self):
        return self.update_epglist()

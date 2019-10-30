# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import json
import os

import defines
import logger

# Writer (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

log = logger.Logger(__name__)


def cmp(a, b):
    return (a > b) - (a < b)


class FDB:
    API_ERROR_INCORRECT = 'incorrect'
    API_ERROR_NOCONNECT = 'noconnect'
    API_ERROR_ALREADY = 'already'
    API_ERROR_NOPARAM = 'noparam'
    API_ERROR_NOFAVOURITE = 'nofavourite'
    MAX_CHANNELS = 30

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
        log.d('delete channel name={0}'.format(name))
        k = self.find(name)
        if k is not None:
            if not self.channels:
                self.get()
            if self.channels:
                del (self.channels[k])
                return self.save()
        return FDB.API_ERROR_NOFAVOURITE

    def moveTo(self, name, to_id):
        to_id -= 1
        if not self.channels:
            self.get()
        if self.channels and to_id < len(self.channels):
            k = self.find(name)
            log.d('moveTo channel from {0} to {1}'.format(k, to_id))
            return self.swapTo(k, to_id)

        return FDB.API_ERROR_NOPARAM

    def find(self, name):
        name = name.lower()
        log.d('find channel by name={0}'.format(name))
        if not self.channels:
            self.get()
        if self.channels:
            for i, ch in enumerate(self.channels):
                if ch['name'].lower() == name:
                    return i

    def swap(self, i1, i2):
        log.d('swap channels with indexes={0}, {1}'.format(i1, i2))
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

    def add(self, ch):
        name = ch.get_name()
        log.d('add channel {0}'.format(name))
        channel = {'name': name, 'pin': True}

        if self.find(name) is None:
            self.channels.append(channel)
            return self.save()

        return FDB.API_ERROR_ALREADY

    def add_recent(self, ch):
        name = ch.get_name()
        log.d('add recent channel {0}'.format(name))
        channel = {'name': name, 'pin': False}

        if self.find(name) is None:
            self.channels.insert(0, channel)
            if len(self.channels) > FDB.MAX_CHANNELS:
                for i in range(len(self.channels), 0, -1):
                    if not self.channels[i].get('pin', True):
                        del self.channels[i]
                        break

            return self.save()

        return FDB.API_ERROR_ALREADY

    def set_pin(self, name, pin):
        log.d('set pin={0} of channel {1}'.format(pin, name))

        ci = self.find(name)
        if ci is not None:
            self.channels[ci]['pin'] = pin
            return self.save()

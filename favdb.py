# -*- coding: utf-8 -*-
# Writer (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru


import json
import defines
import logger
from utils import cmp
from pathlib import Path


log = logger.Logger(__name__)


class FDB:
    API_ERROR_INCORRECT = 'incorrect'
    API_ERROR_NOCONNECT = 'noconnect'
    API_ERROR_ALREADY = 'already'
    API_ERROR_NOPARAM = 'noparam'
    API_ERROR_NOFAVOURITE = 'nofavourite'
    API_NO_REFRESH = 0
    MAX_CHANNELS = 50

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
        log.d(f'delete channel name={name}')
        k = self.find(name)
        if k is not None:
            if not self.channels:
                self.get()
            if self.channels:
                del self.channels[k]
                return self.save()
        return FDB.API_ERROR_NOFAVOURITE

    def moveTo(self, name, to_id):
        to_id -= 1
        if not self.channels:
            self.get()
        if self.channels and to_id < len(self.channels):
            k = self.find(name)
            if k is not None:
                log.d(f'moveTo channel from {k} to {to_id}')
                return self.swapTo(k, to_id)

        return FDB.API_ERROR_NOPARAM

    def find(self, name):
        log.d(f'find channel by name={name}')
        if not self.channels:
            self.get()
        if self.channels:
            return next((i for i, ch in enumerate(self.channels) if ch['name'].lower() == name.lower()), None)

    def swap(self, i1, i2):
        log.d(f'swap channels with indexes={i1}, {i2}')
        try:
            self.channels[i1], self.channels[i2] = self.channels[i2], self.channels[i1]
            return True
        except Exception as e:
            log.w(e)

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
        self.DB = Path(defines.DATA_PATH, 'favdb.json')

    def get(self):
        log.d('get channels')
        if self.DB.exists():
            with self.DB.open(mode='r') as fp:
                try:
                    self.channels = json.load(fp)
                except Exception as e:
                    log.w(f'get error: {e}')
        return self.channels

    def save(self, obj=None):
        log.d('save channels')
        try:
            with self.DB.open(mode='w+') as fp:
                if not obj:
                    obj = self.channels
                json.dump(obj, fp)
                self.channels = obj
                return True
        except Exception as e:
            log.w(f'save error: {e}')
            return FDB.API_ERROR_NOCONNECT

    def add(self, name):
        log.d(f'add channel {name}')
        channel = {'name': name, 'pin': True}

        if self.find(name) is None:
            self.channels.append(channel)
            return self.save()

        return FDB.API_ERROR_ALREADY

    def add_recent(self, name):
        log.d(f'add recent channel {name}')
        channel = {'name': name, 'pin': False}

        if self.find(name) is None:
            self.channels.insert(0, channel)
            if len(self.channels) > FDB.MAX_CHANNELS:
                for i in range(len(self.channels)-1, 0, -1):
                    if not self.channels[i].get('pin', True):
                        del self.channels[i]
                        break

            return self.save()

        return FDB.API_ERROR_ALREADY

    def set_pin(self, name, pin=True):
        log.d(f'set pin={pin} of channel {name}')

        ci = self.find(name)
        if ci is not None:
            self.channels[ci]['pin'] = pin
            return self.save()

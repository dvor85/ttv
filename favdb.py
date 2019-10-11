# -*- coding: utf-8 -*-
# Writer (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import os
import defines
import logger
import xbmc
import utils
import json


log = logger.Logger(__name__)
fmt = utils.fmt


class FDB():
    API_ERROR_INCORRECT = 'incorrect'
    API_ERROR_NOCONNECT = 'noconnect'
    API_ERROR_ALREADY = 'already'
    API_ERROR_NOPARAM = 'noparam'
    API_ERROR_NOFAVOURITE = 'nofavourite'

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
        log.d(fmt('delete channel name={0}', name))
        k = self.find(name)
        if k is not None:
            if not self.channels:
                self.get()
            if self.channels:
                del(self.channels[k])
                return self.save()
        return FDB.API_ERROR_NOFAVOURITE

    def moveTo(self, name, to_id):
        to_id -= 1
        if not self.channels:
            self.get()
        if self.channels and to_id < len(self.channels):
            k = self.find(name)
            log.d(fmt('moveTo channel from {0} to {1}', k, to_id))
            return self.swapTo(k, to_id)

        return FDB.API_ERROR_NOPARAM

    def find(self, name):
        name = utils.lower(name, 'utf8')
        log.d(fmt('find channel by name={0}', name))
        if not self.channels:
            self.get()
        if self.channels:
            for i, ch in enumerate(self.channels):
                if utils.lower(ch['name'], 'utf8') == name:
                    return i

    def swap(self, i1, i2):
        log.d(fmt('swap channels with indexes={0},{1}', i1, i2))
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
                    log.w(fmt('get error: {0}', e))
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
            log.w(fmt('save error: {0}', e))
            return FDB.API_ERROR_NOCONNECT

    def add(self, ch):
        name = ch.get_name()
        log.d(fmt('add channels {0}', name))
        channel = {'name': name}

        if self.find(name) is None:
            self.channels.append(channel)
            return self.save()

        return FDB.API_ERROR_ALREADY

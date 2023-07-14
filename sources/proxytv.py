# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import json
import time
from pathlib import Path
from collections import UserDict
import re
import threading

import defines
import logger
from .tchannel import TChannel, TChannels
import requests

log = logger.Logger(__name__)


class ProxyTV(UserDict):

    _instance = None
    _lock = threading.RLock()

    server = 'https://proxytv.ru/'
    api = f"{server}iptv/php/srch.php"

    __re_group_name_url = re.compile(r'#EXTINF:.*?group-title=\"(?P<group>.*?)\",\<b\>(?P<name>.*?)\-\d+\</b\>\<br\>(?P<url>[\w\.\:/]+)\<br\>')
    __re_name_url = re.compile(r'> (?P<prov>[^\<\>]+)<br><div align=\"left\">.+?#EXTINF:.+?,(?P<name>.+?)\-\d+\<br\>(?P<url>[\w\.\:/]+)\<br\>')
    __re_spaces = re.compile(r'\s{2,}')
    __re_providers = re.compile(r'> (?P<prov>[^\<\>]+),\s*робот\s*\"(?P<robot>[^\<\>]+)\"')
    __re_remove_tags = re.compile(r'\</?[^\>]+\>|\&.*;')

    @classmethod
    def get_instance(cls, *args):
        try:
            if cls._instance is None:
                with cls._lock:
                    if cls._instance is None:
                        cls._instance = cls(*args)
        except Exception as e:
            log.e(f'get_instance error: {e}')
            cls._instance = None
        finally:
            return cls._instance

    def __init__(self):
        UserDict.__init__(self)
        self.sortby = []
        self.sess = requests.Session()
        self.data = {}
        self.providers = {}

    def do_request(self, **params):
        headers = {'Referer': self.server}
        if not self.sess.cookies:
            defines.request(self.server, method='head', session=self.sess, headers=headers)

        return defines.request(self.api, method='post', session=self.sess, params=params, headers=headers)

    def get_channels(self, prov):
        r = self.do_request(udpxyaddr=f"pl:{prov}")
        if r:
            return [{"name": n, "cat": g, "url": u, "src": prov} for g, n, u in self.__re_group_name_url.findall(r.text)]

    def get_providers(self):
        if not self.providers:
            r = self.do_request(udpxyaddr="provider")
            if r:
                self.providers = {prov:robot.lower() for prov, robot  in self.__re_providers.findall(r.text)}
        return self.providers

    def sortby_prov(self, elem):
        try:
            return self.sortby.index(self.get_providers[list(elem.keys())[0]])
        except:
            return -1

    def search_by_name(self, name, sortby=''):
        name = name.lower()
        self.sortby = sortby.split(',')
        log.d(f"search source in proxytv by {name}")

        r = self.do_request(udpxyaddr=f"ch:{name}")
        if r:
            self.data.setdefault(name, [])
            self.data.setdefault(f'{name} hd', [])
            for p, n, u in self.__re_name_url.findall(r.text):
                self.data.setdefault(self.__re_spaces.sub(' ', n.lower().strip()), []).append({p: u})

        self.get_providers()

        self.data[name].sort(key=self.sortby_prov, reverse=True)
        self.data[f'{name} hd'].sort(key=self.sortby_prov, reverse=True)


class Channel(TChannel):
    __re_notprintable = re.compile(r'\</?[^\>]+\>|\&.*;|[^A-Za-zА-Яа-я0-9\+\-\_\(\)\s\.\:\/\*\\|\\\&\%\$\@\!\~\;]')

    def __init__(self, data={}):
        TChannel.__init__(self, data=data, player='tsp')
        self.data['cat'] = self.__re_notprintable.sub('', self.data['cat']).strip().capitalize()
        self.data['name'] = self.__re_notprintable.sub('', self.data['name']).strip().capitalize()


class Channels(TChannels):

    def __init__(self):
        self.proxytv_path = Path(defines.CACHE_PATH, "proxytv_ru.json")
        TChannels.__init__(self, name='proxytv', reload_interval=2592000)
        self.proxytv = ProxyTV.get_instance()

    def _load_jdata(self, avail=True):
        log.d(f'get {self.proxytv_path}')
        if self.proxytv_path.exists():
            if not avail or (time.time() - self.proxytv_path.stat().st_mtime <= self.reload_interval):
                with self.proxytv_path.open(mode='r') as fp:
                    return json.load(fp)
        else:
            log.w(f'{self.proxytv_path} not exists in cache')
        return []

    def _save_jdata(self, jdata):
        if jdata:
            with self.proxytv_path.open(mode='w') as fp:
                json.dump(jdata, fp)

    def update_channels(self):
        self.channels.clear()
        try:
            jdata = self._load_jdata()
            if not jdata:
                jdata = []
                for prov in self.proxytv.get_providers().values():
                    jdata.extend(self.proxytv.get_channels(prov))

                self._save_jdata(jdata)

            if not jdata:
                log.i('Try to load previos channels, if availible')
                jdata = self._load_jdata(False)

            if not jdata:
                log.w("Channels are not avalible")
        except Exception as e:
            log.error(e)

        if jdata:
            self.channels.extend(Channel(_j) for _j in jdata)


# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

#import defines
import sqlite3
from pathlib import Path
from threading import Event, RLock
import defines
import logger


log = logger.Logger(__name__)


class ChannelInfo():
    _instance = None
    _lock = Event()
    _rlock = RLock()

    @staticmethod
    def get_instance():
        if ChannelInfo._instance is None:
            if not ChannelInfo._lock.is_set():
                ChannelInfo._lock.set()
                try:
                    ChannelInfo._instance = ChannelInfo()
                except Exception as e:
                    log.e(f'get_instance error: {e}')
                    ChannelInfo._instance = None
                finally:
                    ChannelInfo._lock.clear()
        return ChannelInfo._instance

    def __init__(self):
        self.db_base = Path(defines.DATA_PATH, 'channel_info.db')
#         self.db_base = Path('~/.kodi/temp/script.torrent-tv.ru.pp/channel_info.db').expanduser()
        self.db = sqlite3.connect(self.db_base, check_same_thread=False)
        with ChannelInfo._rlock:
            with self.db:
                self.db.execute('CREATE TABLE IF NOT EXISTS channels (name TEXT UNIQUE NOT NULL, cat TEXT, title TEXT)')

    def add(self, name, **kwargs):
        log.d(f'add {name}')
        try:
            with ChannelInfo._rlock:
                with self.db:
                    return self.db.execute('INSERT INTO channels VALUES(?, ?, ?)', (name, kwargs.get('cat'), kwargs.get('title', name))).rowcount
        except sqlite3.IntegrityError:
            return

    def delete(self, name):
        log.d(f"delete {name}")
        with ChannelInfo._rlock:
            with self.db:
                return self.db.execute(f'DELETE FROM channels WHERE name="{name}"').rowcount

    def get_info_by_name(self, name):
        with self.db:
            self.db.row_factory = sqlite3.Row
            r = self.db.execute(f'SELECT * FROM channels WHERE name="{name}"')
            info = r.fetchone()
            if info:
                return dict(info)

    def set_info(self, name, **kwargs):
        params = ','.join(f'{k}="{v}"' for k, v in kwargs.items())
        log.d(f'set_info: {params}')
        if self.get_info_by_name(name):
            with ChannelInfo._rlock:
                with self.db:
                    self.db.row_factory = None
                    return self.db.execute(f'UPDATE channels SET {params} WHERE name="{name}"').rowcount
        else:
            return self.add(name, **kwargs)

    def get_groups(self):
        log.d(f'get_groups')
        with self.db:
            self.db.row_factory = None
            r = self.db.execute('SELECT DISTINCT cat from channels WHERE cat not NULL')
            return [i[0] for i in r.fetchall()]
        return []


if __name__ == '__main__':
    db = ChannelInfo()
    print(db.set_info(name='тв-3', title='Привет'))
    print(db.get_info_by_name('тв-3'))
    print(db.get_groups())

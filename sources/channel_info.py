# -*- coding: utf-8 -*-
# Writer (c) 2023, Vorotilin D.V., E-mail: dvor85@mail.ru

import sqlite3
from pathlib import Path
from threading import Event, RLock

try:
    import defines
    import logger
    log = logger.Logger(__name__)
except ImportError:

    class log():

        @staticmethod
        def d(m):
            print(m)


class ChannelInfo():
    _instance = None
    _lock = Event()
    _rlock = RLock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            if not cls._lock.is_set():
                cls._lock.set()
                try:
                    cls._instance = cls()
                except Exception as e:
                    log.e(f'get_instance error: {e}')
                    cls._instance = None
                finally:
                    cls._lock.clear()
        return cls._instance

    def __init__(self, db_base=None):
        self.db_base = db_base if db_base else Path(defines.DATA_PATH, 'channel_info.db')
        self.con = sqlite3.connect(self.db_base, check_same_thread=False)
        with ChannelInfo._rlock:
            with self.con:
                self.con.execute('CREATE TABLE IF NOT EXISTS channels (ch_name TEXT UNIQUE NOT NULL, group_id INT, ch_title TEXT, ch_enable INT)')
                self.con.execute('CREATE TABLE IF NOT EXISTS groups (group_name TEXT UNIQUE NOT NULL, group_title TEXT, group_enable INT)')

    def add_channel(self, name, **kwargs):
        if name is not None:
            name = name.lower()
            log.d(f'add_channel {name}')
            try:
                with ChannelInfo._rlock:
                    with self.con:
                        grid = kwargs.get('group_id')
                        if not grid and 'group_name' in kwargs:
                            grinfo = self.get_group_by_name(kwargs['group_name'])
                            grid = grinfo['id'] if grinfo else self.add_group(kwargs['group_name'])
                        return self.con.execute('INSERT INTO channels VALUES(?, ?, ?, ?)', (name, grid, kwargs.get('ch_title'), kwargs.get('ch_enable', 1))).rowcount
            except sqlite3.IntegrityError:
                return

    def add_group(self, name, **kwargs):
        if name is not None:
            name = name.lower()
            log.d(f'add_group {name}')
            try:
                with ChannelInfo._rlock:
                    with self.con:
                        return self.con.execute('INSERT INTO groups VALUES(?, ?, ?)', (name, kwargs.get('group_title'), kwargs.get('group_enable', 1))).lastrowid
            except sqlite3.IntegrityError:
                return

    def get_channel_by_name(self, name):
        if name is not None:
            name = name.lower()
            return next(self.get_channels(where=f'ch_name="{name}"'), None)

    def get_group_by_name(self, name):
#         log.d(f"get_group_by_name {name}")
        if name is not None:
            name = name.lower()
            return next(self.get_groups(where=f'group_name="{name}" or group_title="{name}"'), None)

    def delete_group_info(self, name):
        if name is not None:
            name = name.lower()
            log.d(f"delete_group_info {name}")
            return self.set_group_info(name, group_title=None)

    def delete_ch_info(self, name):
        if name is not None:
            name = name.lower()
            log.d(f"delete_ch_info {name}")
            sqls = [f'DELETE FROM channels WHERE ch_name="{name}"']
            with ChannelInfo._rlock:
                with self.con:
                    return all(self.con.execute(s).rowcount for s in sqls)

    def set_channel_info(self, name, **kwargs):
        if name is not None:
            name = name.lower()
            params = ','.join(f'{k}="{str(v).lower()}"' if v is not None else f'{k}=NULL' for k, v in kwargs.items() if 'ch' in k or 'group_id' in k)
            log.d(f'set_channel_info  for {name}: {params}')
            if self.get_channel_by_name(name):
                with ChannelInfo._rlock:
                    with self.con:
                        self.con.row_factory = None
                        if params:
                            return self.con.execute(f'UPDATE channels SET {params} WHERE ch_name="{name}"').rowcount
            else:
                return self.add_channel(name, **kwargs)

    def set_group_info(self, name, **kwargs):
        if name is not None:
            name = name.lower()
            params = ','.join(f'{k}="{str(v).lower()}"' if v is not None else f'{k}=NULL' for k, v in kwargs.items() if 'group' in k)
            log.d(f'set_group_info for {name}: {params}')
            if self.get_group_by_name(name):
                with ChannelInfo._rlock:
                    with self.con:
                        self.con.row_factory = None
                        if params:
                            return self.con.execute(f'UPDATE groups SET {params} WHERE group_name="{name}" or group_title="{name}"').rowcount
            else:
                return self.add_group(name, **kwargs)

    def get_groups(self, where=''):
        if where:
            where = f'WHERE {where}'
        with ChannelInfo._rlock:
            with self.con:
                self.con.row_factory = sqlite3.Row
                r = self.con.execute(f'SELECT rowid as id,* from groups {where}')
                for i in r.fetchall():
                    yield dict(i)

    def get_channels(self, where=''):
        if where:
            where = f'WHERE {where}'
        with ChannelInfo._rlock:
            with self.con:
                self.con.row_factory = sqlite3.Row
                r = self.con.execute(f'SELECT * from channels LEFT JOIN groups on channels.group_id=groups.rowid {where}')
                for i in r.fetchall():
                    yield dict(i)


if __name__ == '__main__':
    db = ChannelInfo(db_base=Path('~/.kodi/temp/script.torrent-tv.ru.pp/channel_info.con').expanduser())

    print(list(db.get_groups()))
    print(list(db.get_channels()))
    print(db.get_channel_by_name('euronews по-русски'))

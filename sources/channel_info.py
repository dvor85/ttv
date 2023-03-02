# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

#import defines
import sqlite3
from pathlib import Path
from threading import Event, RLock
# import defines
# import logger


# log = logger.Logger(__name__)


class log():
    @staticmethod
    def d(m):
        print(m)


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
        #         self.db_base = Path(defines.DATA_PATH, 'channel_info.db')
        self.db_base = Path('~/.kodi/temp/script.torrent-tv.ru.pp/channel_info.db').expanduser()
        self.db = sqlite3.connect(self.db_base, check_same_thread=False)
        with ChannelInfo._rlock:
            with self.db:
                self.db.execute('CREATE TABLE IF NOT EXISTS channels (ch_name TEXT UNIQUE NOT NULL, group_id INT, ch_title TEXT, ch_enable INT)')
                self.db.execute('CREATE TABLE IF NOT EXISTS groups (group_name TEXT UNIQUE NOT NULL, group_title TEXT, group_enable INT)')

    def add_channel(self, name, **kwargs):
        name = name.lower()
        log.d(f'add_channel {name}')
        try:
            with ChannelInfo._rlock:
                with self.db:
                    grid = None
                    if 'group_name' in kwargs:
                        grinfo = self.get_group_by_name(kwargs['group_name'])
                        grid = grinfo['id'] if grinfo else self.add_group(kwargs['group_name'])
                    return self.db.execute('INSERT INTO channels VALUES(?, ?, ?, ?)', (name, grid, kwargs.get('ch_title'), kwargs.get('ch_enable', 1))).rowcount
        except sqlite3.IntegrityError:
            return

    def add_group(self, name, **kwargs):
        name = name.lower()
        log.d(f'add_group {name}')
        try:
            with ChannelInfo._rlock:
                with self.db:
                    return self.db.execute('INSERT INTO groups VALUES(?, ?, ?)', (name, kwargs.get('group_title'), kwargs.get('group_enable', 1))).lastrowid
        except sqlite3.IntegrityError:
            return

    def get_group_by_name(self, name):
        name = name.lower()
        with self.db:
            self.db.row_factory = sqlite3.Row
            r = self.db.execute(f'SELECT rowid as id, * FROM groups WHERE group_name="{name}" or group_title="{name}"')
            info = r.fetchone()
            if info:
                return dict(info)

    def delete_group_info(self, name):
        name = name.lower()
        log.d(f"delete_group_info {name}")
        with ChannelInfo._rlock:
            with self.db:
                return self.db.execute(f'DELETE FROM groups WHERE group_name="{name}"').rowcount

    def delete_ch_info(self, name):
        name = name.lower()
        log.d(f"delete_ch_info {name}")
        sqls = [f'DELETE FROM channels WHERE ch_name="{name}"']
        with ChannelInfo._rlock:
            with self.db:
                chinfo = self.get_channel_by_name(name)
                if chinfo and chinfo['group_id']:
                    sqls.append(f'DELETE FROM groups WHERE rowid={chinfo["group_id"]}')
                return all(self.db.execute(s).rowcount for s in sqls)

    def get_channel_by_name(self, name):
        name = name.lower()
        with self.db:
            self.db.row_factory = sqlite3.Row
            r = self.db.execute(f'SELECT * FROM channels LEFT JOIN groups ON group_id=groups.rowid WHERE ch_name="{name}" or ch_title="{name}"')
            info = r.fetchone()
            if info:
                return dict(info)

    def set_channel_info(self, name, **kwargs):
        name = name.lower()
        ch_params = ','.join(f'{k}="{str(v).lower()}"' for k, v in kwargs.items() if 'ch' in k)
        log.d(f'set_channel_info  for {name}: {ch_params}')
        if self.get_channel_by_name(name):
            with ChannelInfo._rlock:
                with self.db:
                    self.db.row_factory = None
                    if 'group_name' in kwargs:
                        self.set_group_info(name=kwargs['group_name'], **kwargs)
                    return self.db.execute(f'UPDATE channels SET {ch_params} WHERE ch_name="{name}" or ch_title="{name}"').rowcount
        else:
            return self.add_channel(name, **kwargs)

    def set_group_info(self, name, **kwargs):
        name = name.lower()
        params = ','.join(f'{k}="{str(v).lower()}"' for k, v in kwargs.items() if 'group' in k)
        log.d(f'set_group_info for {name}: {params}')
        if self.get_group_by_name(name):
            with ChannelInfo._rlock:
                with self.db:
                    self.db.row_factory = None
                    return self.db.execute(f'UPDATE groups SET {params} WHERE group_name="{name}" or group_title="{name}"').rowcount
        else:
            return self.add_group(name, **kwargs)

    def get_groups(self, **kwfilter):
        params = ','.join(f'{k}="{str(v).lower()}"' for k, v in kwfilter.items() if 'group' in k)
        log.d(f'get_groups {params}')

        with self.db:
            self.db.row_factory = sqlite3.Row
            where = f'WHERE {params}' if params else ""
            r = self.db.execute(f'SELECT rowid as id,* from groups {where}')
            return [dict(i) for i in r.fetchall()]
        return []

    def get_channels(self):
        log.d(f'get_channels')
        with self.db:
            self.db.row_factory = sqlite3.Row
            r = self.db.execute('SELECT * from channels left join groups on channels.group_id=groups.rowid')
            return [dict(i) for i in r.fetchall()]
        return []


if __name__ == '__main__':
    from pprint import pprint as print
    db = ChannelInfo()
    print(db.add_channel(name='привет', group_name='приветствия'))
    print(db.add_channel(name='здравствуй', group_name='приветствия'))
#     print(db.set_channel_info(name='тв-3', title='Привет'))
#     print(db.get_channel_by_name('тв-3'))
    print(db.get_groups())
    print(db.get_channels())
    print(db.get_channel_by_name('euronews по-русски'))

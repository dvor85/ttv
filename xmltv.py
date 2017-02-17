# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
import datetime
import time
import string

import sqlite3
import os

fmt = string.Formatter().format


class XMLTV():

    def __init__(self):
        self.xmltv_file = 'ttv.xmltv.xml'
        xmltv_tree = ET.parse(self.xmltv_file)
        self.xmltv_root = xmltv_tree.getroot()

    def get_channels(self):
        for chid in self.xmltv_root.iter('channel'):
            for name in chid.iter('display-name'):
                yield {'chid': chid.get('id'), 'name': name.text}

    def get_epg_by_id(self, chid):
        ctime = datetime.datetime.now()
        prev_bt = 0
        prev_et = 0
        for programme in self.xmltv_root.iter('programme'):
            if programme.get('channel') == chid:
                ep = {}

                bt = programme.get('start').split()
                bt = datetime.datetime.strptime(bt[0], "%Y%m%d%H%M%S") + datetime.timedelta(hours=-3 + 4)
                ep['btime'] = time.mktime(bt.timetuple())

                et = programme.get('stop').split()
                et = datetime.datetime.strptime(et[0], "%Y%m%d%H%M%S") + datetime.timedelta(hours=-3 + 4)
                ep['etime'] = time.mktime(et.timetuple())

                ep['name'] = programme.iter('title').next().text

                if et > ctime and abs((bt.date() - ctime.date()).days) <= 1 and prev_et <= float(ep['btime']) > prev_bt:
                    yield ep
                    prev_bt = float(ep['btime'])
                    prev_et = float(ep['etime'])


class EPGBase():
    TABLE_CHANNELS = 'channels'
    TABLE_EPG = 'epg'
    TABLE_UPDATES = 'updates'

    def __init__(self):
        self.base = 'epg.db'
        self.xmltv = None

        self.conn = sqlite3.connect(self.base)  # @UndefinedVariable
        self.conn.row_factory = sqlite3.Row  # @UndefinedVariable
        sql = []
        self.last_upd_tm = self.get_last_update()

        if self.last_upd_tm is not None and (datetime.datetime.now() - self.last_upd_tm).days >= 3:
            sql.append(
                fmt('drop table if exists {table};',
                    table=EPGBase.TABLE_EPG))

        sql.append(
            fmt("create table if not exists {table} \
                    (channel_id varchar(32) PRIMARY KEY, name varchar(32) NOT NULL);",
                table=EPGBase.TABLE_CHANNELS))
        sql.append(
            fmt("create table if not exists {table} \
                    (channel_id varchar(32) NOT NULL, btime real NOT NULL, etime real NOT NULL, name varchar(128));",
                table=EPGBase.TABLE_EPG))
        sql.append(
            fmt("create table if not exists {table} \
                    (last_update real NOT NULL);",
                table=EPGBase.TABLE_UPDATES))

        with self.conn:
            self.conn.executescript("".join(sql))

        self.add_channels()

    def get_xmltv(self):
        if self.xmltv is None:
            self.xmltv = XMLTV()
        return self.xmltv

    def add_channels(self):
        if self.last_upd_tm is None:

            with self.conn:
                for ch in self.get_xmltv().get_channels():
                    try:
                        sql = fmt("insert into {table} values('{chid}', '{name}')",
                                  table=EPGBase.TABLE_CHANNELS, chid=ch['chid'], name=ch['name'])
                        self.conn.execute(sql)
                    except Exception as e:
                        print e
            self.set_last_update()

    def get_id_by_name(self, name):
        try:
            sql = fmt("select channel_id from {channels} \
                             where name='{name}' limit 1",
                      channels=EPGBase.TABLE_CHANNELS, name=name)
            with self.conn:
                return self.conn.execute(sql).fetchone()['channel_id']
        except Exception as e:
            print e
            return None

    def set_last_update(self):
        self.last_upd_tm = time.time()
        with self.conn:
            sql = fmt("insert into {table} values({last_update})",
                      table=EPGBase.TABLE_UPDATES, last_update=self.last_upd_tm)
            self.conn.execute(sql)

    def get_last_update(self):
        res = None
        try:
            sql = fmt("select last_update from {table} \
                             order by last_update DESC limit 1",
                      table=EPGBase.TABLE_UPDATES)
            with self.conn:
                res = datetime.datetime.fromtimestamp(self.conn.execute(sql).fetchone()['last_update'])
        except Exception as e:
            print e
        finally:
            return res

    def add_epg(self, chid, epg):
        sql = []
        with self.conn:
            for ep in epg:
                sql = fmt("insert into {table} values('{chid}', {btime}, {etime}, '{name}')",
                          table=EPGBase.TABLE_EPG, chid=chid, btime=ep['btime'], etime=ep['etime'], name=ep['name'])

                self.conn.execute(sql)

    def get_epg_by_id(self, chid):
        res = []
        try:
            sql = fmt("select btime, etime, {epg}.name from {channels} inner join {epg} \
                             on {channels}.channel_id={epg}.channel_id where {channels}.channel_id='{chid}'",
                      channels=EPGBase.TABLE_CHANNELS, epg=EPGBase.TABLE_EPG, chid=chid)
            with self.conn:
                cur = self.conn.execute(sql)
                res = cur.fetchone()
                if res is None:
                    self.add_epg(chid, self.get_xmltv().get_epg_by_id(chid))
                    cur = self.conn.execute(sql)
                    res = cur.fetchone()

                while res is not None:
                    yield res
                    res = cur.fetchone()

        except Exception as e:
            print e
            yield None

    def get_epg_by_name(self, name):
        return self.get_epg_by_id(self.get_id_by_name(name))

if __name__ == '__main__':
    epg_base = EPGBase()

    for epg in (epg_base.get_epg_by_name('National Geographic HD'), epg_base.get_epg_by_name('Первый канал')):
        for ep in epg:
            bt = datetime.datetime.fromtimestamp(float(ep['btime']))
            et = datetime.datetime.fromtimestamp(float(ep['etime']))
            print u"{0} - {1} {2}".format(bt.strftime("%H:%M"), et.strftime("%H:%M"), ep['name'].replace('&quot;', '"'))

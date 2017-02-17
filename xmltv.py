# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
import datetime
import time
import string

import sqlite3
import os

fmt = string.Formatter().format


class EPGBase():
    TABLE_CHANNELS = 'channels'
    TABLE_EPG = 'epg'

    def __init__(self):
        self.base = 'epg.db'
        self.conn = sqlite3.connect(self.base)  # @UndefinedVariable
        sql = []
        sql.append(
            fmt("create table if not exists {base} \
                    (channel_id varchar(32) PRIMARY KEY, title varchar(32) NOT NULL)",
                base=EPGBase.TABLE_CHANNELS))
        sql.append(
            fmt("create table if not exists {base} \
                    (channel_id varchar(32) PRIMARY KEY, btime real NOT NULL, etime real NOT NULL, title varchar(128))",
                base=EPGBase.TABLE_EPG))

        with self.conn:
            for s in sql:
                self.conn.execute(s)


tree = ET.parse('ttv.xmltv.xml')
root = tree.getroot()
epg = []

# for chid in root.iter('channel'):
#     print "id = {0}".format(chid.get('id'))
#     for name in chid.iter('display-name'):
#         print u"name = {0}".format(name.text)


for programme in root.iter('programme'):
    if programme.get('channel') == 'ttv7663':
        ep = {}
        bt = programme.get('start').split()
        ep['btime'] = time.mktime(
            (datetime.datetime.strptime(bt[0], "%Y%m%d%H%M%S") + datetime.timedelta(hours=-3 + 4)).timetuple())
        et = programme.get('stop').split()
        ep['etime'] = time.mktime(
            (datetime.datetime.strptime(et[0], "%Y%m%d%H%M%S") + datetime.timedelta(hours=-3 + 4)).timetuple())
        ep['name'] = programme.iter('title').next().text
        epg.append(ep)

for ep in epg:
    bt = datetime.datetime.fromtimestamp(float(ep['btime']))
    et = datetime.datetime.fromtimestamp(float(ep['etime']))
    print u"{0} - {1} {2}".format(bt.strftime("%H:%M"), et.strftime("%H:%M"), ep['name'].replace('&quot;', '"'))

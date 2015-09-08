# -*- coding: utf-8 -*-

import defines
import os
import sqlite3

LogToXBMC = defines.Logger('FavDB')

class FavDB(object):

    def __init__(self):
        self.DB = os.path.join(defines.DATA_PATH, 'favdb.db')
        self.conn = None
        self.create()
        
        
    def create(self):
        if not os.path.exists(self.DB):
            cur = self.connect()
            cur.execute('CREATE TABLE fav (id text)')
            self.conn.commit()
            self.conn.close()
        
    def connect(self):
        if not self.conn:
            self.conn = sqlite3.connect(self.DB)
        return self.conn.cursor()    
        
    def putChannels(self, channels):        
        purchases = []
        for ch in channels:
            purchases.append((ch.getProperty('id'),))
        cur = self.connect()
        cur.execute('DELETE FROM fav')
        cur.executemany('INSERT INTO fav values (?)', purchases)
        self.conn.commit()
        self.conn.close()     
    
    def getChannels(self):
        cur = self.connect()
        cur.execute('SELECT * FROM fav')
        res = cur.fetchone()
        while res:
            yield res[0]
            res = cur.fetchone()
        self.conn.close()
    
    def searchChannel(self, num):
        cur = self.connect()
        cur.execute('SELECT * FROM fav where id=?', (num,))
        res = cur.fetchone()
        self.conn.close()
        return res
    
    def addChannel(self, num):
        cur = self.connect()
        cur.execute('INSERT INTO fav values (?)', (num,))
        self.conn.commit()
        self.conn.close()
            
    def deleteChannel(self, num):
        cur = self.connect()
        cur.execute('DELETE FROM fav where id=(?)', (num,))
        self.conn.commit()
        self.conn.close()
        
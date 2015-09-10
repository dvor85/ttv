# -*- coding: utf-8 -*-
# Copyright (c) 2013 Torrent-TV.RU
# Writer (c) 2013, Welicobratov K.A., E-mail: 07pov23@gmail.com
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import xbmcgui
import xbmc
import defines
import favdb
import json

log = defines.Logger('MenuForm')

class MenuForm(xbmcgui.WindowXMLDialog):
    CMD_ADD_FAVOURITE = 'favourite_add.php'
    CMD_DEL_FAVOURITE = 'favourite_delete.php'
    CMD_UP_FAVOURITE = 'favourite_up.php'
    CMD_DOWN_FAVOURITE = 'favourite_down.php'
    CONTROL_CMD_LIST = 301
    
    def __init__(self, *args, **kwargs):
        self.li = None
        self.result = 'FAIL'
        self.parent = None
        

    def onInit(self):
        log.d('OnInit')
        if not self.li or not self.parent:
            return
        try:
            cmds = self.li.getProperty('commands').split(',')
            list = self.getControl(MenuForm.CONTROL_CMD_LIST)
            list.reset()
            for c in cmds:
                if c == MenuForm.CMD_ADD_FAVOURITE:
                    title = 'Добавить в избранное'
                elif c == MenuForm.CMD_DEL_FAVOURITE:
                    title = 'Удалить из избранного'
                elif c == MenuForm.CMD_UP_FAVOURITE:
                    title = 'Поднять вверх'
                elif c == MenuForm.CMD_DOWN_FAVOURITE:
                    title = 'Опустить вниз'
                list.addItem(xbmcgui.ListItem(title, c))
            list.setHeight(cmds.__len__() * 38)
            list.selectItem(0)
            self.setFocusId(MenuForm.CONTROL_CMD_LIST)
            log.d('Focus Controld %s' % self.getFocusId())
        except Exception, e: 
            log.e("В списке нет комманд %s" % e)
        
    def onClick(self, controlId):
        log.d('OnClick')
        log('ControlID = %s' % controlId, xbmc.LOGDEBUG)
        if controlId == MenuForm.CONTROL_CMD_LIST:
            lt = self.getControl(MenuForm.CONTROL_CMD_LIST)
            li = lt.getSelectedItem()
            cmd = li.getLabel2()
            log("cmd=%s" % cmd, xbmc.LOGDEBUG)
            
            self._sendCmd(cmd)
            self.close()

    def _sendCmd(self, cmd):        
        log.d('sendCmd')
        channel_id = self.li.getLabel2()
        data = defines.GET('http://api.torrent-tv.ru/v3/%s?session=%s&channel_id=%s&typeresult=json' % (cmd, self.parent.session, channel_id), cookie=self.parent.session)
        log.d(data)
        log.d('http://api.torrent-tv.ru/v3/%s?session=%s&channel_id=%s&typeresult=json' % (cmd, self.parent.session, channel_id))
        try:
            jdata = json.loads(data)
        except Exception as e:
            log.e(e)
            return
        if jdata['success'] == 0:
            self.result = jdata['error'].encode('utf-8')
            if not self.parent.user["vip"]:
                self._exec_in_favdb(cmd)
        else:
            self.result = 'OK REMOTE'
            
    def _exec_in_favdb(self, cmd):
        log.d('exec in favdb')
        fdb = favdb.FavDB()    
        if cmd == MenuForm.CMD_ADD_FAVOURITE:
            if fdb.add(self.li):
                self.result = 'OK LOCAL'
        elif cmd == MenuForm.CMD_DEL_FAVOURITE:
            k = fdb.find(int(self.li.getProperty('id')))
            if not k is None and fdb.delete(k):
                self.result = 'OK LOCAL'
        elif cmd == MenuForm.CMD_UP_FAVOURITE:
            if fdb.up(self.li):
                self.result = 'OK LOCAL'
        elif cmd == MenuForm.CMD_DOWN_FAVOURITE:
            if fdb.down(self.li):
                self.result = 'OK LOCAL'
                    

    def GetResult(self):
        if not self.result:
            self.result = 'FAIL'
        res = self.result
        self.result = 'FAIL'
        return res

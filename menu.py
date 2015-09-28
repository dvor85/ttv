# -*- coding: utf-8 -*-
# Copyright (c) 2013 Torrent-TV.RU
# Writer (c) 2013, Welicobratov K.A., E-mail: 07pov23@gmail.com
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import xbmcgui
import defines
import favdb

log = defines.Logger('MenuForm')

class MenuForm(xbmcgui.WindowXMLDialog):
    CMD_ADD_FAVOURITE = 'favourite_add'
    CMD_DEL_FAVOURITE = 'favourite_delete'
    CMD_MOVE_FAVOURITE = 'favourite_move'
    CONTROL_CMD_LIST = 301
    
    def __init__(self, *args, **kwargs):
        self.li = None
        self.result = None
        self.parent = None
        

    def onInit(self):
        log.d('OnInit')
        if not self.li or not self.parent:
            return
        log.d("li = %s" % self.li.getProperty("commands"))
        try:
            cmds = self.li.getProperty('commands').split(',')
            lst = self.getControl(MenuForm.CONTROL_CMD_LIST)
            lst.reset()
            for c in cmds:
                if c == MenuForm.CMD_ADD_FAVOURITE:
                    title = 'Добавить в избранное'
                elif c == MenuForm.CMD_DEL_FAVOURITE:
                    title = 'Удалить из избранного'
                elif c == MenuForm.CMD_MOVE_FAVOURITE:
                    title = 'Переместить'
                lst.addItem(xbmcgui.ListItem(title, c))
            lst.setHeight(len(cmds) * 38)
            lst.selectItem(0)
            self.setFocusId(MenuForm.CONTROL_CMD_LIST)
            log.d('Focus Controld %s' % self.getFocusId())
        except Exception, e: 
            log.e("В списке нет комманд %s" % e)
        
    def onClick(self, controlId):
        log.d('OnClick')
        log.d('ControlID = %s' % controlId)
        if controlId == MenuForm.CONTROL_CMD_LIST:
            lt = self.getControl(MenuForm.CONTROL_CMD_LIST)
            li = lt.getSelectedItem()
            cmd = li.getLabel2()
            log.d("cmd=%s" % cmd)
            
            self.result = self.exec_cmd(cmd)
            self.close()

    def exec_cmd(self, cmd):
        try:
            if self.parent.user["vip"]:
                fdb = favdb.RemoteFDB(self.parent.session)
            else:
                fdb = favdb.LocalFDB()
                
            if cmd == MenuForm.CMD_ADD_FAVOURITE:
                return fdb.add(self.li)
            elif cmd == MenuForm.CMD_DEL_FAVOURITE:
                return fdb.delete(self.li)
            elif cmd == MenuForm.CMD_MOVE_FAVOURITE:
                to_num = int(xbmcgui.Dialog().numeric(0, heading='Введите позицию'))
                return fdb.moveTo(self.li, to_num)
        except Exception as e:
            log.e('Error: {0} in exec_cmd "{1}"'.format(e, cmd))
                    

    def GetResult(self):
        if self.result == True:
            self.result = 'OK'
        elif not self.result:
            self.result = 'FAIL'
        res = self.result
        self.result = None
        return res 


  # -*- coding: utf-8 -*-
# Copyright (c) 2013 Torrent-TV.RU
# Writer (c) 2013, Welicobratov K.A., E-mail: 07pov23@gmail.com
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import xbmcgui
import xbmc
import json
import os
import defines

log = defines.Logger('MenuForm')

class MenuForm(xbmcgui.WindowXMLDialog):
    CMD_ADD_FAVOURITE = 'favourite_add.php'
    CMD_DEL_FAVOURITE = 'favourite_delete.php'
    CMD_UP_FAVOURITE = 'favourite_up.php'
    CMD_DOWN_FAVOURITE = 'favourite_down.php'
    CMD_CLOSE_TS = 'close_ts'
    CONTROL_CMD_LIST = 301
    def __init__(self, *args, **kwargs):
        self.li = None
        self.get_method = None
        self.session = None
        self.result = 'None'
        self.DB = os.path.join(defines.DATA_PATH, 'favdb.json')
        pass

    def onInit(self):
        if not self.li:
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
                elif c == MenuForm.CMD_CLOSE_TS:
                    title = 'Завершить TS'
                list.addItem(xbmcgui.ListItem(title, c))
            list.setHeight(cmds.__len__() * 38)
            list.selectItem(0)
            self.setFocusId(MenuForm.CONTROL_CMD_LIST)
            log.d('Focus Controld %s' % self.getFocusId())
        except Exception, e: 
            log.e("В списке нет комманд %s" % e)
            pass
        
    def onClick(self, controlId):
        log('ControlID = %s' % controlId, xbmc.LOGDEBUG)
        if controlId == MenuForm.CONTROL_CMD_LIST:
            lt = self.getControl(MenuForm.CONTROL_CMD_LIST)
            li = lt.getSelectedItem()
            cmd = li.getLabel2()
            log("cmd=%s" % cmd, xbmc.LOGDEBUG)
    
            if cmd == MenuForm.CMD_CLOSE_TS: 
                self.CloseTS()
            else:
                self._sendCmd(cmd)
            self.close()

    def _sendCmd(self, cmd):
        channel_id = self.li.getLabel2()
        res = self.get_method('http://api.torrent-tv.ru/v3/%s?session=%s&channel_id=%s&typeresult=json' % (cmd, self.session, channel_id), cookie=self.session)
        log.d(res)
        log('http://api.torrent-tv.ru/v3/%s?session=%s&channel_id=%s&typeresult=json' % (cmd, self.session, channel_id))
        jdata = json.loads(res)
        if jdata['success'] == 0:
            self.result = jdata['error']
            self._execCmd(cmd)
        else:
            self.result = 'OK'
            
    def _execCmd(self, cmd):
        jdata = []
        def _find(chid):
            for obj in jdata:
                if obj['id'] == chid:
                    return obj
            
        channel = {'id': int(self.li.getProperty('id')), 'type': self.li.getProperty('type'), 'logo': os.path.basename(self.li.getProperty('icon')), 'access_translation': "registred", 'access_user': 1, 'name': self.li.getProperty('name'), 'epg_id': int(self.li.getProperty('epg_cdn_id'))}
        mode = 'w'
        if os.path.exists(self.DB):
            mode = 'r'
            
        with open(self.DB, mode) as fp:
            try:
                jdata = json.load(fp)
            except Exception as e:
                log.w(e)
            if cmd == MenuForm.CMD_ADD_FAVOURITE:
                jdata.append(channel)
            elif cmd == MenuForm.CMD_DEL_FAVOURITE:
                jdata.remove(_find(channel['id']))
        with open(self.DB, 'w') as fp:
            json.dump(jdata, fp)
        self.result = 'OK'

    def CloseTS(self):
        log('Closet TS')
        self.result = 'TSCLOSE'

    def GetResult(self):
        if not self.result:
            self.result = 'None'
        res = self.result
        self.result = 'None'
        return res.encode('utf-8')

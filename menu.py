# -*- coding: utf-8 -*-
# Copyright (c) 2013 Torrent-TV.RU
# Writer (c) 2013, Welicobratov K.A., E-mail: 07pov23@gmail.com
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import xbmcgui
from utils import uni, str2

import favdb
import logger
from sources import tchannel


log = logger.Logger(__name__)


class MenuForm(xbmcgui.WindowXMLDialog):
    CMD_ADD_FAVOURITE = 'favourite_add'
    CMD_DEL_FAVOURITE = 'favourite_delete'
    CMD_MOVE_FAVOURITE = 'favourite_move'
    CMD_UP_FAVOURITE = 'favourite_up'
    CMD_DOWN_FAVOURITE = 'favourite_down'
    CMD_SET_TRUE_PIN = 'set_pin_true'
    CMD_SET_FALSE_PIN = 'set_pin_false'
    CONTROL_CMD_LIST = 301

    def __init__(self, xmlFilename, scriptPath, *args, **kwargs):
        super(MenuForm, self).__init__(xmlFilename, scriptPath)
        self.li = None
        self.channel = None
        self.result = None
        self.parent = None

    def onInit(self):
        log.d('OnInit')
        if not self.li or not self.parent:
            return
        self.channel = tchannel.TChannel({"name": uni(self.li.getProperty("name"))})
        log.d("li = {0}".format(uni(self.li.getProperty("commands"))))
        try:
            cmds = uni(self.li.getProperty('commands')).split(',')
            lst = self.getControl(MenuForm.CONTROL_CMD_LIST)
            lst.reset()
            title = None
            for c in cmds:
                if c == MenuForm.CMD_ADD_FAVOURITE:
                    title = 'Добавить в избранное'
                elif c == MenuForm.CMD_DEL_FAVOURITE:
                    title = 'Удалить из избранного'
                elif c == MenuForm.CMD_MOVE_FAVOURITE:
                    title = 'Переместить'
                elif c == MenuForm.CMD_UP_FAVOURITE:
                    title = 'Поднять'
                elif c == MenuForm.CMD_DOWN_FAVOURITE:
                    title = 'Опустить'
                elif c == MenuForm.CMD_SET_TRUE_PIN:
                    title = 'Заблокировать'
                elif c == MenuForm.CMD_SET_FALSE_PIN:
                    title = 'Разблокировать'
                if title:
                    lst.addItem(xbmcgui.ListItem(str2(title), str2(c)))

            self.getControl(999).setHeight(len(cmds) * 40 + 55)
            lst.setHeight(len(cmds) * 40 + 55)
            lst.selectItem(0)
            self.setFocusId(MenuForm.CONTROL_CMD_LIST)
            log.d('Focus ControlId {0}'.format(uni(self.getFocusId())))
        except Exception as e:
            log.e("В списке нет комманд {0}".format(uni(e)))
            self.close()

    def onClick(self, controlId):
        if controlId == MenuForm.CONTROL_CMD_LIST:
            lt = self.getControl(MenuForm.CONTROL_CMD_LIST)
            li = lt.getSelectedItem()
            cmd = uni(li.getLabel2())
            log.d("cmd={0}".format(cmd))

            self.result = self.exec_cmd(cmd)
            self.close()

    def exec_cmd(self, cmd):
        try:
            #             if utils.str2int(defines.FAVOURITE) == 0 and self.parent.user["vip"]:
            #                 fdb = favdb.RemoteFDB(self.parent.session)
            #             else:
            fdb = favdb.LocalFDB()

            if cmd == MenuForm.CMD_ADD_FAVOURITE:
                return fdb.add(self.channel)
            elif cmd == MenuForm.CMD_DEL_FAVOURITE:
                return fdb.delete(self.channel.get_name())
            elif cmd == MenuForm.CMD_MOVE_FAVOURITE:
                to_num = int(xbmcgui.Dialog().numeric(0, heading=str2('Введите позицию')))
                return fdb.moveTo(self.channel.get_name(), to_num)
            elif cmd == MenuForm.CMD_DOWN_FAVOURITE:
                return fdb.down(self.channel.get_name())
            elif cmd == MenuForm.CMD_UP_FAVOURITE:
                return fdb.up(self.channel.get_name())
            elif cmd == MenuForm.CMD_SET_TRUE_PIN:
                return fdb.set_pin(self.channel.get_name(), True)
            elif cmd == MenuForm.CMD_SET_FALSE_PIN:
                return fdb.set_pin(self.channel.get_name(), False)
        except Exception as e:
            log.e('Error: {0} in exec_cmd "{1}"'.format(uni(e), cmd))
            self.close()

    def GetResult(self):
        res = 'OK' if self.result else 'FAIL'
        self.result = None
        return res

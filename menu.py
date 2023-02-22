# -*- coding: utf-8 -*-
# Copyright (c) 2013 Torrent-TV.RU
# Writer (c) 2013, Welicobratov K.A., E-mail: 07pov23@gmail.com
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import xbmcgui

import favdb
import logger
from sources import tchannel
from sources.channel_info import ChannelInfo


log = logger.Logger(__name__)


class MenuForm(xbmcgui.WindowXMLDialog):
    CMD_ADD_FAVOURITE = 'favourite_add'
    CMD_DEL_FAVOURITE = 'favourite_delete'
    CMD_MOVE_FAVOURITE = 'favourite_move'
    CMD_UP_FAVOURITE = 'favourite_up'
    CMD_DOWN_FAVOURITE = 'favourite_down'
    CMD_SET_TRUE_PIN = 'set_pin_true'
    CMD_SET_FALSE_PIN = 'set_pin_false'
    CMD_MOVE_TO_GROUP = 'move_to_group'
    CONTROL_CMD_LIST = 301

    def __init__(self, xmlFilename, scriptPath, *args, **kwargs):
        super(MenuForm, self).__init__(xmlFilename, scriptPath)
        self.chinfo = ChannelInfo()
        self.li = None
        self.channel = None
        self.result = None
        self.parent = None

    def onInit(self):
        log.d('OnInit')
        if not self.li or not self.parent:
            return
        self.channel = tchannel.TChannel({"name": self.li.getProperty("title")})
        log.d(f"li = {self.li.getProperty('commands')}")
        try:
            cmds = self.li.getProperty('commands').split(',')
            cmds.append(MenuForm.CMD_MOVE_TO_GROUP)
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
                elif c == MenuForm.CMD_MOVE_TO_GROUP:
                    title = 'Переместить в категорию'
                if title:
                    lst.addItem(xbmcgui.ListItem(title, c))

            self.getControl(999).setHeight(len(cmds) * 40 + 55)
            lst.setHeight(len(cmds) * 40 + 55)
            lst.selectItem(0)
            self.setFocusId(MenuForm.CONTROL_CMD_LIST)
            log.d(f'Focus ControlId {self.getFocusId()}')
        except Exception as e:
            log.e(f"В списке нет комманд {e}")
            self.close()

    def onClick(self, controlId):
        if controlId == MenuForm.CONTROL_CMD_LIST:
            lt = self.getControl(MenuForm.CONTROL_CMD_LIST)
            li = lt.getSelectedItem()
            cmd = li.getLabel2()
            log.d(f"cmd={cmd}")

            self.result = self.exec_cmd(cmd)
            self.close()

    def move_to_group(self, name):
        dialog = xbmcgui.Dialog()
        samples = self.chinfo.get_groups() + ['Введите свое название']
        ret = dialog.contextmenu(samples)
        if ret > -1:
            if ret < len(samples)-1:
                return self.chinfo.set_group(name, samples[ret])
            else:
                cat = dialog.input(samples[ret]).capitalize()
                if cat:
                    return self.chinfo.set_group(name, cat)

    def exec_cmd(self, cmd):
        try:
            fdb = favdb.LocalFDB()

            if cmd == MenuForm.CMD_ADD_FAVOURITE:
                return fdb.add(self.channel.title())
            elif cmd == MenuForm.CMD_DEL_FAVOURITE:
                return fdb.delete(self.channel.title())
            elif cmd == MenuForm.CMD_MOVE_FAVOURITE:
                to_num = int(xbmcgui.Dialog().numeric(0, heading='Введите позицию'))
                return fdb.moveTo(self.channel.title(), to_num)
            elif cmd == MenuForm.CMD_DOWN_FAVOURITE:
                return fdb.down(self.channel.title())
            elif cmd == MenuForm.CMD_UP_FAVOURITE:
                return fdb.up(self.channel.title())
            elif cmd == MenuForm.CMD_SET_TRUE_PIN:
                return fdb.set_pin(self.channel.title())
            elif cmd == MenuForm.CMD_SET_FALSE_PIN:
                return fdb.set_pin(self.channel.title(), False)
            elif cmd == MenuForm.CMD_MOVE_TO_GROUP:
                return self.move_to_group(self.channel.name().lower())
        except Exception as e:
            log.e(f'Error: {e} in exec_cmd "{cmd}"')
            self.close()

    def GetResult(self):
        res = 'OK' if self.result else 'FAIL'
        self.result = None
        return res

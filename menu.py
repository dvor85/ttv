# -*- coding: utf-8 -*-
# Created (c) 2023, Vorotilin D.V., E-mail: dvor85@mail.ru

import xbmcgui
import favdb
import logger
from sources.channel_info import ChannelInfo


log = logger.Logger(__name__)


class MenuForm(xbmcgui.Dialog):
    CMD_ADD_FAVOURITE = 'favourite_add'
    CMD_DEL_FAVOURITE = 'favourite_delete'
    CMD_MOVE_FAVOURITE = 'favourite_move'
    CMD_UP_FAVOURITE = 'favourite_up'
    CMD_DOWN_FAVOURITE = 'favourite_down'
    CMD_SET_TRUE_PIN = 'set_pin_true'
    CMD_SET_FALSE_PIN = 'set_pin_false'
    CMD_MOVE_TO_GROUP = 'move_to_group'
    CMD_RENAME_TITLE = 'rename_title'
    CMD_DELETE_CHINFO = 'delete_chinfo'

    def __init__(self, li, parent):
        self.li = li
        self.parent = parent
        self.chinfo = ChannelInfo().get_instance()
        self.result = None
        self.fdb = favdb.LocalFDB()
        self.entries = {MenuForm.CMD_ADD_FAVOURITE: {'title': 'Добавить в избранное', 'action': self.fdb.add},
                        MenuForm.CMD_DEL_FAVOURITE: {'title': 'Удалить из избранного', 'action': self.fdb.delete},
                        MenuForm.CMD_MOVE_FAVOURITE: {'title': 'Переместить', 'action': self.fav_move},
                        MenuForm.CMD_UP_FAVOURITE: {'title': 'Поднять', 'action': self.fdb.up},
                        MenuForm.CMD_DOWN_FAVOURITE: {'title': 'Опустить', 'action': self.fdb.down},
                        MenuForm.CMD_SET_TRUE_PIN: {'title': 'Заблокировать', 'action': self.fdb.set_pin},
                        MenuForm.CMD_SET_FALSE_PIN: {'title': 'Разблокировать', 'action': lambda x: self.fdb.set_pin(x, False)},
                        MenuForm.CMD_MOVE_TO_GROUP: {'title': 'Переместить в категорию', 'action': self.move_to_group},
                        MenuForm.CMD_RENAME_TITLE: {'title': 'Переименовать', 'action': self.rename_title},
                        MenuForm.CMD_DELETE_CHINFO: {'title': 'Очистить информацию', 'action': self.chinfo.delete}
                        }

    def show(self):
        log.d('show')
        if not self.li or not self.parent or self.li.getProperty('type') != 'channel':
            return

        log.d(f"li = {self.li.getProperty('commands')}")
        cmds = self.li.getProperty('commands').split(',')
        cmds.extend([MenuForm.CMD_MOVE_TO_GROUP, MenuForm.CMD_RENAME_TITLE, MenuForm.CMD_DELETE_CHINFO])

        lst = [self.entries[c] for c in cmds if c in self.entries]
        ret = self.contextmenu([c['title'] for c in lst])
        if ret > -1:
            self.result = lst[ret]['action'](self.li.getProperty("name").lower())

    def move_to_group(self, name):
        samples = list(set(self.chinfo.get_groups()).union(self.parent.channel_groups.getGroups()).difference(
            (self.parent.SEARCH_GROUP, self.parent.FAVOURITE_GROUP))) + ['Введите свое название']
        ret = self.contextmenu(samples)
        if ret > -1:
            if ret < len(samples)-1:
                return self.chinfo.set_info(name, cat=samples[ret])
            else:
                cat = self.input(samples[ret]).capitalize()
                if cat:
                    return self.chinfo.set_info(name, cat=cat)

    def rename_title(self, name):
        dialog = xbmcgui.Dialog()
        title = dialog.input('Введите новое название').lower()
        if title:
            return self.chinfo.set_info(name, title=title)

    def fav_move(self, name):
        to_num = int(self.numeric(0, heading='Введите позицию'))
        return self.fdb.moveTo(name, to_num)

    def GetResult(self):
        return 'OK' if self.result else 'FAIL'

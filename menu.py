# -*- coding: utf-8 -*-
# Created (c) 2023, Vorotilin D.V., E-mail: dvor85@mail.ru

import xbmcgui
import favdb
import logger
import defines
import utils
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
    CMD_RENAME_CH_TITLE = 'rename_ch_title'
    CMD_DELETE_CHINFO = 'delete_chinfo'
    CMD_DELETE_GROUP_INFO = 'delete_group_info'
    CMD_RENAME_GROUP = 'rename_group'
    CMD_DISABLE_CHANNEL = 'disable_channel'
    CMD_ENABLE_CHANNEL = 'enable_channel'
    CMD_DISABLE_GROUP = 'disable_group'
    CMD_ENABLE_GROUP = 'enable_group'

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
                        MenuForm.CMD_SET_TRUE_PIN: {'title': 'Запретить автоудаления', 'action': self.fdb.set_pin},
                        MenuForm.CMD_SET_FALSE_PIN: {'title': 'Разрешить автоудаления', 'action': lambda x: self.fdb.set_pin(x, False)},
                        MenuForm.CMD_MOVE_TO_GROUP: {'title': 'Переместить в категорию', 'action': self.move_to_group},
                        MenuForm.CMD_RENAME_CH_TITLE: {'title': 'Переименовать', 'action': self.rename_ch_title},
                        MenuForm.CMD_RENAME_GROUP: {'title': 'Переименовать', 'action': self.rename_group_title},
                        MenuForm.CMD_DELETE_CHINFO: {'title': 'Сбросить изменения', 'action': self.chinfo.delete_ch_info},
                        MenuForm.CMD_DELETE_GROUP_INFO: {'title': 'Сбросить изменения', 'action': self.chinfo.delete_group_info},
                        MenuForm.CMD_DISABLE_CHANNEL:  {'title': 'Отключить', 'action': lambda x: self.set_ch_enabled(x, 0)},
                        MenuForm.CMD_ENABLE_CHANNEL:  {'title': 'Включить', 'action': lambda x: self.set_ch_enabled(x, 1)},
                        MenuForm.CMD_DISABLE_GROUP:  {'title': 'Отключить', 'action': lambda x: self.set_group_enabled(x, 0)},
                        MenuForm.CMD_ENABLE_GROUP:  {'title': 'Включить', 'action': self.enable_group},

                        }

    def show(self):
        log.d('show')
        if not self.li or not self.parent:
            return
        log.d(f"commands = {self.li.getProperty('commands')}")
        log.d(f"enabled = {self.li.getProperty('enabled')}")
        cmds = self.li.getProperty('commands').split(',')

        if self.li.getProperty('type') == 'channel':
            cmds.extend([MenuForm.CMD_MOVE_TO_GROUP, MenuForm.CMD_RENAME_CH_TITLE, MenuForm.CMD_DELETE_CHINFO])

        elif self.li.getProperty('type') == 'category':
            cmds.extend([MenuForm.CMD_RENAME_GROUP, MenuForm.CMD_DELETE_GROUP_INFO, MenuForm.CMD_ENABLE_GROUP, MenuForm.CMD_DISABLE_GROUP])

        if utils.str2int(defines.AGE) < 2:
            if MenuForm.CMD_ENABLE_GROUP in cmds:
                cmds.remove(MenuForm.CMD_ENABLE_GROUP)
            if MenuForm.CMD_ENABLE_CHANNEL in cmds:
                cmds.remove(MenuForm.CMD_ENABLE_CHANNEL)

        lst = [self.entries[c] for c in cmds if c in self.entries]
        ret = self.contextmenu([c['title'] for c in lst])
        if ret > -1:
            self.result = lst[ret]['action'](self.li.getProperty("name").lower())

    def move_to_group(self, name):
        group_titles = [gr['group_title'].capitalize() if gr.get('group_title') else gr['group_name'].capitalize() for gr in self.chinfo.get_groups()]
        samples = list(set(group_titles).union(self.parent.channel_groups.getGroups()).difference(
            (self.parent.SEARCH_GROUP, self.parent.FAVOURITE_GROUP))) + ['Введите свое название']
        ret = self.contextmenu(samples)
        if ret > -1:
            cat = samples[ret] if ret < len(samples)-1 else self.input(samples[ret])
            if cat:
                grinfo = self.chinfo.get_group_by_name(cat)
                grid = grinfo['id'] if grinfo else self.chinfo.add_group(cat)
                if grid:
                    return self.chinfo.set_channel_info(name, group_id=grid)

    def rename_ch_title(self, name):
        title = self.input('Введите новое название')
        if title:
            return self.chinfo.set_channel_info(name, ch_title=title.lower())

    def set_ch_enabled(self, name, state):
        return self.chinfo.set_channel_info(name, ch_enable=state)

    def set_group_enabled(self, name, state):
        return self.chinfo.set_group_info(name, group_enable=state)

    def enable_group(self, *args):
        samples = list(set([gr['group_title'].capitalize() if gr.get('group_title') else gr['group_name'].capitalize()
                            for gr in self.chinfo.get_groups('group_enable=0')]))
        if samples:
            ret = self.contextmenu(samples)
            if ret > -1:
                if ret < len(samples):
                    res = self.set_group_enabled(samples[ret], 1)
                    return res
        else:
            self.notification(heading='Сообщение', message='Нечего включать')

    def rename_group_title(self, name):
        title = self.input('Введите новое название')
        if title:
            return self.chinfo.set_group_info(name, group_title=title.lower())

    def fav_move(self, name):
        to_num = int(self.numeric(0, heading='Введите позицию'))
        return self.fdb.moveTo(name, to_num)

    def GetResult(self):
        return 'OK' if self.result else 'FAIL'

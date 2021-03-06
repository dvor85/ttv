# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import datetime
import json
import threading
import xbmcgui
import xbmc
from operator import methodcaller
from six import itervalues, iteritems, iterkeys, next
from collections import OrderedDict
from utils import uni, str2

import defines
import favdb
import logger
import utils
import yatv
from menu import MenuForm
from playerform import MyPlayer
from sources.tchannel import TChannel, MChannel
from sources.table import channel_sources


log = logger.Logger(__name__)


class ChannelGroups(OrderedDict):
    """
    :return {
            groupname: {
                title=str,
                channels=[mchannel,...]
            }
    }
    """

    def addGroup(self, groupname, title=None):

        self[groupname] = {}
        if not title:
            title = groupname
        self[groupname]['title'] = title
        self.clearGroup(groupname)

    def clearGroup(self, groupname):
        self[groupname]['channels'] = []

    def delGroup(self, groupname):
        del self[groupname]

    def getGroups(self):
        return list(self.keys())

    def addChannels(self, channels, src_name):
        for ch in channels:
            self.addChannel(ch, src_name)
        return True if channels else False

    def addChannel(self, ch, src_name, groupname=None):
        try:
            if groupname is None:
                groupname = ch.group()
            if groupname is None:
                groupname = src_name
            if groupname.lower() in ["18+"] and utils.str2int(defines.AGE) < 2:
                return
            if groupname not in self:
                self.addGroup(groupname)
            src_index = channel_sources.index_by_name(src_name)
            try:
                c = next(self.find_channel_by_title(groupname, ch.title()))
            except StopIteration:
                c = None
            if c:
                c.insert(src_index, ch)
            else:
                if not isinstance(ch, MChannel):
                    self.getChannels(groupname).append(MChannel({src_index: ch}))
                else:
                    self.getChannels(groupname).append(ch)
        except Exception as e:
            log.error("addChannel from source:{0} error: {1}".format(src_name, uni(e)))

    def getSortedChannels(self, groupname):
        if groupname == WMainForm.FAVOURITE_GROUP:
            return self.getChannels(groupname)
        else:
            return sorted(self.getChannels(groupname), key=methodcaller('title'))

    def getChannels(self, groupname):
        try:
            return self[groupname]["channels"]
        except KeyError:
            return []

    def find_channel_by_id(self, groupname, chid):
        for ch in self.getChannels(groupname):
            if ch.id() == chid:
                yield ch

    def find_group_by_name(self, name):
        for groupname in (x for x in self.getGroups() if x not in (WMainForm.FAVOURITE_GROUP, WMainForm.SEARCH_GROUP)):
            try:
                if next(self.find_channel_by_name(groupname, name)):
                    yield groupname
            except StopIteration:
                pass

    def find_group_by_chtitle(self, chtitle):
        for groupname in (x for x in self.getGroups() if x not in (WMainForm.FAVOURITE_GROUP, WMainForm.SEARCH_GROUP)):
            try:
                if next(self.find_channel_by_title(groupname, chtitle)):
                    yield groupname
            except StopIteration:
                pass

    def find_channel_by_name(self, groupname, name):
        name = name.lower()
        for ch in self.getChannels(groupname):
            if ch.name().lower() == name.lower():
                yield ch

    def find_channel_by_title(self, groupname, title):
        for ch in self.getChannels(groupname):
            if title.lower() in ch.title().lower():
                yield ch


class RotateScreen(threading.Thread):

    def __init__(self, img_control, screens):
        threading.Thread.__init__(self)
        self.active = False
        self.name = 'RotateScreen'
        self.img_control = img_control
        self.screens = screens
        self.daemon = False

    def run(self):
        self.active = True
        while self.active:
            for screen in self.screens:
                if self.active:
                    self.img_control.setImage(str2(screen))
                    if defines.monitor.waitForAbort(2):
                        self.stop()

    def stop(self):
        self.active = False
        self.img_control.setImage('')


class LoopPlay(threading.Thread):

    def __init__(self, parent):
        threading.Thread.__init__(self)
        self.active = False
        self.daemon = False
        self.parent = parent
        self.name = 'LoopPlay'

    def stop(self):
        log.d("stop from {0}".format(self.name))
        self.active = False
        self.parent.player.channelStop()

    def run(self):
        self.active = True
        while self.active and not defines.isCancel():
            try:
                selItem = self.parent.list.getListItem(self.parent.selitem_id)
                if selItem and selItem.getProperty('type') == "channel":
                    self.parent.cur_channel = uni(selItem.getProperty('title'))
                    sel_ch = self.parent.get_channel_by_title(self.parent.cur_channel)
                    if not sel_ch:
                        msg = "Канал временно не доступен"
                        self.parent.showStatus(msg)
                        raise Exception("{msg}. Возможно не все каналы загрузились...".format(msg=msg))

                    defines.ADDON.setSetting('cur_category', str2(self.parent.cur_category))
                    defines.ADDON.setSetting('cur_channel', str2(self.parent.cur_channel))
                    if not self.parent.player.Start(sel_ch):
                        break
                    self.parent.player.close()
                if not defines.isCancel():
                    xbmc.sleep(223)
                    self.parent.select_channel()

            except Exception as e:
                log.e('LoopPlay error: {0}'.format(uni(e)))
                xbmc.sleep(1000)

        self.parent.player.close()
        #         self.parent.show()

        if xbmc.getCondVisibility("Window.IsVisible(home)"):
            log.d("Close from HOME Window")
            self.parent.close()
        elif xbmc.getCondVisibility("Window.IsVisible(video)"):
            self.parent.close()
            log.d("Is Video Window")
        elif xbmc.getCondVisibility("Window.IsVisible(programs)"):
            self.parent.close()
            log.d("Is programs Window")
        elif xbmc.getCondVisibility("Window.IsVisible(addonbrowser)"):
            self.parent.close()
            log.d("Is addonbrowser Window")
        elif xbmc.getCondVisibility("Window.IsVisible(12345)"):
            self.parent.close()
            log.d("Is plugin Window")
        else:
            jrpc = json.loads(xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"GUI.GetProperties","params":{"properties":["currentwindow"]},"id":1}'))
            if jrpc["result"]["currentwindow"]["id"] == 10025:
                log.d("Is video plugins window")
                self.parent.close()


class WMainForm(xbmcgui.WindowXML):
    CANCEL_DIALOG = (9, 10, 11, 92, 216, 247, 257, 275, 61467, 61448,)
    CONTEXT_MENU_IDS = (117, 101)
    ARROW_ACTIONS = (1, 2, 3, 4)
    DIGIT_BUTTONS = list(range(58, 68))
    ACTION_MOUSE = 107
    BTN_VOD_ID = 113
    BTN_CLOSE = 101
    BTN_FULLSCREEN = 208
    IMG_SCREEN = 210
    IMG_LOGO = 1111
    CONTROL_LIST = 50

    TXT_PROGRESS = 107
    IMG_PROGRESS = 108
    PROGRESS_BAR = 110
    DESC_LABEL = 105

    BTN_INFO = 209
    LBL_FIRST_EPG = 300

    SEARCH_GROUP = 'Поиск'
    FAVOURITE_GROUP = 'Избранное'

    API_ERROR_INCORRECT = 'incorrect'
    API_ERROR_NOCONNECT = 'noconnect'
    API_ERROR_ALREADY = 'already'
    API_ERROR_NOPARAM = 'noparam'
    API_ERROR_NOFAVOURITE = 'nofavourite'

    TIMER_GET_EPG = __name__ + ':get_epg_timer'
    TIMER_SHOW_SCREEN = __name__ + ':show_screen_timer'
    TIMER_SEL_CHANNEL = __name__ + ':sel_channel_timer'
    TIMER_HIDE_WINDOW = __name__ + ':hide_window_timer'
    TIMER_ADD_RECENT = 'add_recent_timer'
    THREAD_SET_LOGO = 'set_logo_thread'

    def __init__(self, *args, **kwargs):
        log.d('__init__')
        self.channel_groups = ChannelGroups()
        self.img_progress = None
        self.txt_progress = None
        self.progress = None
        self.list = None
        self.list_type = ''
        self.player = MyPlayer("player.xml", defines.ADDON_PATH, "st.anger")
        self.player.parent = self
        self.cur_category = None
        self.cur_channel = None
        self.selitem_id = -1
        self.user = None
        self.first_init = defines.AUTOSTART_LASTCH
        self.channel_number_str = ''
        self.set_logo_sema = threading.Semaphore(24)

        self.timers = defines.Timers()
        self.rotate_screen_thr = None
        self.loop_play_thr = None
        self._yatv_instance = None

    def onInit(self):
        log.d('onInit')
        self.cur_category = uni(defines.ADDON.getSetting('cur_category'))
        self.cur_channel = uni(defines.ADDON.getSetting('cur_channel'))
        self.img_progress = self.getControl(WMainForm.IMG_PROGRESS)
        self.txt_progress = self.getControl(WMainForm.TXT_PROGRESS)
        self.progress = self.getControl(WMainForm.PROGRESS_BAR)
        self.description_label = self.getControl(WMainForm.DESC_LABEL)

        self.list = self.getControl(WMainForm.CONTROL_LIST)
        self.init = True

        if not self.channel_groups:
            self.updateList()
        else:
            self.loadList()

        self.hide_main_window(timeout=10)

    def get_selitem_id(self, title):
        for index in range(1, self.list.size()):
            li = self.list.getListItem(index)
            if uni(li.getProperty('title')) == title:
                return index
        else:
            return -1

    def get_channel_by_title(self, chtitle):
        categ = self.cur_category
        if self.cur_category in (WMainForm.FAVOURITE_GROUP, WMainForm.SEARCH_GROUP):
            try:
                categ = next(self.channel_groups.find_group_by_chtitle(chtitle))
            except StopIteration:
                pass
        try:
            return next(self.channel_groups.find_channel_by_title(categ, chtitle))
        except StopIteration:
            return None

    def showDialog(self, msg):
        from okdialog import OkDialog
        dialog = OkDialog("dialog.xml", defines.ADDON_PATH, "st.anger")
        dialog.setText(str2(msg))
        dialog.doModal()

    def onFocus(self, ControlID):
        if self.rotate_screen_thr:
            self.rotate_screen_thr.stop()
            self.rotate_screen_thr = None
        self.timers.stop(WMainForm.TIMER_SHOW_SCREEN)

        for controlId in (WMainForm.IMG_SCREEN,):
            self.getControl(controlId).setImage('')

        self.showNoEpg()
        if ControlID == WMainForm.CONTROL_LIST:
            if not self.list:
                return
            selItem = self.list.getSelectedItem()
            if selItem and selItem.getProperty('type') == 'channel':

                sel_ch = self.get_channel_by_title(uni(selItem.getProperty("title")))
                if sel_ch:
                    self.getEpg(sel_ch, timeout=0.5, callback=self.showEpg)

                for controlId in (WMainForm.IMG_SCREEN,):
                    # selItem.getArt('icon') return empty string (kodi 18.5)
                    self.getControl(controlId).setImage(selItem.getProperty('icon'))

    def loadFavourites(self, *args):
        for ch in favdb.LocalFDB().get():
            try:
                self.channel_groups.addChannel(TChannel(ch), src_name='fav', groupname=WMainForm.FAVOURITE_GROUP)
            except Exception as e:
                log.d('loadFavourites error: {0}'.format(uni(e)))

    def loadSearch(self, *args):
        self.timers.stop(WMainForm.TIMER_HIDE_WINDOW)
        self.channel_groups.clearGroup(WMainForm.SEARCH_GROUP)
        if len(args) > 0:
            chtitle = args[0]
        else:
            chtitle = uni(xbmcgui.Dialog().input(heading=str2('введите название канала')))
        if chtitle:
            for gr in self.channel_groups.find_group_by_chtitle(chtitle):
                for ch in self.channel_groups.find_channel_by_title(gr, chtitle):
                    try:
                        self.channel_groups.addChannel(ch, src_name='search', groupname=WMainForm.SEARCH_GROUP)
                    except Exception as e:
                        log.d('loadFavourites error: {0}'.format(uni(e)))

    def loadChannels(self, *args):
        src_name = args[0]
        log.d('loadChannels {0}'.format(src_name))
        src = channel_sources.get_by_name(src_name)
        try:
            res = self.channel_groups.addChannels(src.get_channels(), src_name=src_name)
            timeout = src.reload_interval if res else 60
            if timeout > 0:
                name = 'reload_channels_{0}'.format(src_name)
                self.timers.stop(name)
                self.timers.start(name, threading.Timer(timeout, self.loadChannels, args=args))

        except Exception as e:
            log.d('loadChannels {0} error: {1}'.format(src_name, e))

    def getEpg(self, ch, timeout=0, callback=None):

        def get():
            chnum = self.player.channel_number
            try:
                epg = None
                log.d('getEpg->get')
                self.showStatus('Загрузка программы')
                if ch:
                    epg = ch.epg()
                    if callback is not None and chnum == self.player.channel_number:
                        callback(ch, epg)
                    self.getEpg(ch, 60, callback)
            except Exception as e:
                log.d('getEpg->get error: {0}'.format(uni(e)))
            finally:
                #                     self.get_epg_lock.clear()
                self.hideStatus()

        self.timers.stop(WMainForm.TIMER_GET_EPG)
        self.timers.start(WMainForm.TIMER_GET_EPG, threading.Timer(timeout, get))

    def showEpg(self, ch, curepg):
        try:
            ctime = datetime.datetime.now()
            for i, ep in enumerate(curepg):
                try:
                    ce = self.getControl(WMainForm.LBL_FIRST_EPG + i)
                    bt = datetime.datetime.fromtimestamp(float(ep['btime']))
                    et = datetime.datetime.fromtimestamp(float(ep['etime']))
                    ce.setLabel(str2("{0} - {1} {2}".format(bt.strftime("%H:%M"),
                                                            et.strftime("%H:%M"),
                                                            ep['name'].replace('&quot;', '"'))))
                    if i == 0:
                        if self.progress:
                            self.progress.setPercent((ctime - bt).seconds * 100 // (et - bt).seconds)
                        if 'screens' not in ep:
                            screens = ch.get_screenshots()
                            if screens:
                                ep['screens'] = screens

                        if 'screens' in ep:
                            self.showScreen(ep['screens'], 1)
                        if self.description_label and 'desc' in ep:
                            self.description_label.setText(str2(ep['desc']))

                except:
                    break

            return True

        except Exception as e:
            log.e('showEpg error {0}'.format(uni(e)))

    def showNoEpg(self):
        for i in range(99):
            try:
                ce = self.getControl(WMainForm.LBL_FIRST_EPG + i)
                if i == 0:
                    ce.setLabel(str2('Нет программы'))
                else:
                    ce.setLabel('')
            except:
                break
        if self.progress:
            self.progress.setPercent(0)
        if self.description_label:
            self.description_label.setText('')

    def showScreen(self, screens, timeout=0):

        def show():
            log.d('showScreen')

            if screens:
                if self.rotate_screen_thr:
                    self.rotate_screen_thr.stop()
                    self.rotate_screen_thr.join(0.2)
                    self.rotate_screen_thr = None

                img_screen = self.getControl(WMainForm.IMG_SCREEN)
                self.rotate_screen_thr = RotateScreen(img_screen, screens)
                self.rotate_screen_thr.start()

        self.timers.stop(WMainForm.TIMER_SHOW_SCREEN)
        self.timers.start(WMainForm.TIMER_SHOW_SCREEN, threading.Timer(timeout, show))

    def updateList(self):

        def dump_channel_groups():
            namedb = {}
            for cat, val in iteritems(self.channel_groups):
                for ch in val['channels']:
                    namedb[ch.name().lower()] = {'logo': ch.logo(), 'cat': cat}
                    break
            import os
            s = json.dumps(namedb, indent=4, ensure_ascii=False)
            with open(os.path.join(defines.DATA_PATH, 'namedb.json'), 'wb') as fp:
                fp.write(s)

        def LoadOther():
            for name, thr in iteritems(thrs):
                if name not in ('yatv_epg',):
                    thr.join(20)

        #             dump_channel_groups()

        self.showStatus("Получение списка каналов")

        for groupname in (WMainForm.SEARCH_GROUP, WMainForm.FAVOURITE_GROUP):
            title = '[COLOR FFFFFF00][B]' + groupname + '[/B][/COLOR]'
            self.channel_groups.addGroup(groupname, title)

        thrs = OrderedDict()
        thrs['favourite'] = defines.MyThread(self.loadFavourites)
        thrs['yatv_epg'] = defines.MyThread(lambda: setattr(self, '_yatv_instance', yatv.YATV.get_instance()))

        for src in channel_sources:
            thrs[src.name] = defines.MyThread(self.loadChannels, src.name)

        for thr in itervalues(thrs):
            thr.start()

        lo_thr = defines.MyThread(LoadOther)
        lo_thr.start()

        log.d('Ожидание результата')
        if self.cur_category == WMainForm.FAVOURITE_GROUP:
            thrs['favourite'].join(20)
        else:
            lo_thr.join(len(thrs) * 20)

        if self.cur_category == WMainForm.SEARCH_GROUP:
            self.loadSearch(self.cur_channel)

        self.loadList()

    def loadList(self):
        if self.cur_category == '' or self.cur_category not in self.channel_groups.getGroups():
            self.fillCategory()
        else:
            self.fillChannels()
            if self.init:
                self.select_channel()
                self.init = False
            if self.list and (0 < self.selitem_id < self.list.size()):
                if self.first_init:  # автостарт канала
                    self.first_init = False
                    self.startChannel()
        self.hideStatus()

    def Play(self):
        if self.loop_play_thr:
            self.loop_play_thr.stop()
            self.loop_play_thr.join(2)

        self.loop_play_thr = LoopPlay(self)
        self.loop_play_thr.start()

    def startChannel(self):
        self.select_channel()
        self.Play()

    def select_channel(self, sch='', timeout=0):

        def clear():
            self.channel_number_str = ''

        if not self.list_type == 'channels':
            return
        if self.channel_number_str == '':
            self.channel_number_str = sch if sch != '' else self.selitem_id
        log('CHANNEL NUMBER IS: {0}'.format(self.channel_number_str))
        chnum = utils.str2int(self.channel_number_str)

        if 0 < chnum < self.list.size():
            self.selitem_id = chnum
            self.setFocus(self.list)
            self.list.selectItem(self.selitem_id)

        self.timers.stop(WMainForm.TIMER_SEL_CHANNEL)
        self.timers.start(WMainForm.TIMER_SEL_CHANNEL, threading.Timer(timeout, clear))

    def hide_main_window(self, timeout=0):
        log.d('hide main window in {0} sec'.format(timeout))

        def isPlaying():
            return not defines.isCancel() and self.player._player and self.player._player.isPlaying()

        def hide():
            log.d('isPlaying={0}'.format(isPlaying()))
            if isPlaying():
                for name in iterkeys(self.timers):
                    if name.startswith(__name__):
                        self.timers.stop(name)

                if self.rotate_screen_thr:
                    self.rotate_screen_thr.stop()
                log.d('hide main window')
                self.player.Show()

        self.timers.stop(WMainForm.TIMER_HIDE_WINDOW)
        self.timers.start(WMainForm.TIMER_HIDE_WINDOW, threading.Timer(timeout, hide))

    def add_recent_channel(self, channel, timeout=0):
        log.d('add_resent_channel in {0} sec'.format(timeout))

        def add():
            if not self.cur_category == WMainForm.FAVOURITE_GROUP:
                if favdb.LocalFDB().add_recent(channel.title()):
                    self.channel_groups.clearGroup(WMainForm.FAVOURITE_GROUP)
                    self.loadFavourites()

        self.timers.stop(WMainForm.TIMER_ADD_RECENT)
        self.timers.start(WMainForm.TIMER_ADD_RECENT, threading.Timer(timeout, add))

    def onClick(self, controlID):
        log.d('onClick {0}'.format(controlID))
        if controlID == 200:
            self.setFocusId(WMainForm.CONTROL_LIST)
            self.player.manualStop()
        elif controlID == WMainForm.CONTROL_LIST:
            selItem = self.list.getSelectedItem()

            if not selItem:
                return
            log.d("selItem is {0}".format(uni(selItem.getLabel())))

            if uni(selItem.getLabel()) == '..':
                self.fillCategory()
                return

            if WMainForm.SEARCH_GROUP in uni(selItem.getLabel()):
                self.loadSearch()

            if uni(selItem.getProperty('type')) == 'category':
                self.cur_category = uni(selItem.getProperty("id"))
                self.selitem_id = -1
                self.fillChannels()
                return

            self.selitem_id = self.list.getSelectedPosition()
            self.Play()

        elif controlID == WMainForm.BTN_FULLSCREEN:
            self.player.Show()

        elif controlID == WMainForm.BTN_INFO:
            self.showInfoWindow()
            return

    def showMenuWindow(self):
        mnu = MenuForm("menu.xml", defines.ADDON_PATH, "st.anger")
        mnu.li = self.getFocus().getSelectedItem()
        mnu.parent = self
        selitemid = self.list.getSelectedPosition()

        log.d('Выполнить команду')
        mnu.doModal()
        log.d('Комманда выполнена')
        res = mnu.GetResult()
        log.d('Результат команды {0}'.format(res))
        if res.startswith('OK'):

            self.channel_groups.clearGroup(WMainForm.FAVOURITE_GROUP)
            fthr = defines.MyThread(self.loadFavourites)
            fthr.start()
            if self.cur_category == WMainForm.FAVOURITE_GROUP:
                fthr.join(10)
                self.loadList()

        elif res == WMainForm.API_ERROR_INCORRECT:
            self.showStatus('Пользователь не опознан по сессии')
        elif res == WMainForm.API_ERROR_NOCONNECT:
            self.showStatus('Ошибка соединения с БД')
        elif res == WMainForm.API_ERROR_ALREADY:
            self.showStatus('Канал уже был добавлен в избранное ранее')
        elif res == WMainForm.API_ERROR_NOPARAM:
            self.showStatus('Ошибка входных параметров')
        elif res == WMainForm.API_ERROR_NOFAVOURITE:
            self.showStatus('Канал не найден в избранном')

        if self.list.size() > selitemid:
            self.setFocus(self.list)
            self.list.selectItem(selitemid)

    def onAction(self, action):
        #         log.d('Событие {0}'.format(action.getId()))

        if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_BACKSPACE, xbmcgui.ACTION_PARENT_DIR):
            selItem = self.list.getListItem(0)
            if selItem and uni(selItem.getLabel()) == "..":
                self.fillCategory()
                return

        if action in WMainForm.CANCEL_DIALOG:
            log.d('ACTION CLOSE FORM')
            self.close()
        elif action in (xbmcgui.ACTION_STOP, xbmcgui.ACTION_PAUSE):
            self.player.manualStop()

        if not defines.isCancel():
            if action.getButtonCode() == 61513:
                return
            elif action in WMainForm.ARROW_ACTIONS:
                self.onFocus(self.getFocusId())
            elif action in WMainForm.CONTEXT_MENU_IDS and self.getFocusId() == WMainForm.CONTROL_LIST:
                if action == 101:
                    return
                self.showMenuWindow()

            elif action == WMainForm.ACTION_MOUSE:
                if self.getFocusId() == WMainForm.CONTROL_LIST:
                    self.onFocus(WMainForm.CONTROL_LIST)
            elif action in WMainForm.DIGIT_BUTTONS:
                # IN PRESSING DIGIT KEYS ############ @IgnorePep8
                self.channel_number_str += str2(action.getId() - 58)
                self.select_channel(timeout=1)
            else:
                super(WMainForm, self).onAction(action)

            self.hide_main_window(timeout=10)

    def showStatus(self, text):
        try:
            log.d("showStatus: {0}".format(text))
            if self.img_progress:
                self.img_progress.setVisible(True)
            if self.txt_progress:
                self.txt_progress.setLabel(str2(text))
        except Exception as e:
            log.w("showStatus error: {0}".format(uni(e)))

    def hideStatus(self):
        try:
            if self.img_progress:
                self.img_progress.setVisible(False)
            if self.txt_progress:
                self.txt_progress.setLabel("")
        except Exception as e:
            log.w("hideStatus error: {0}".format(uni(e)))

    def fillChannels(self):
        self.showStatus("Заполнение списка")
        if not self.list:
            self.showStatus("Список не инициализирован")
            return
        log.d('fillChannels: Clear list')
        self.list.reset()
        self.list_type = 'channels'
        li = xbmcgui.ListItem('..')
        self.list.addItem(li)
        i = 0

        for ch in self.channel_groups.getSortedChannels(self.cur_category):
            if ch:
                # не добавлять чистые каналы с ttv
                #                 if len(ch) == 1 and ch[0].src() in ['ttv']:
                #                     continue
                try:
                    if defines.isCancel():
                        return
                    i += 1
                    chname = "{0}. {1}".format(i, ch.title())
                    chli = xbmcgui.ListItem(str2(chname))
                    self.setLogo(ch, chli, self.set_logo_sema)
                    chli.setProperty('type', 'channel')
#                     chli.setProperty("id", str2(ch.id()))
                    chli.setProperty("name", str2(ch.name()))
                    chli.setProperty("title", str2(ch.title()))
                    if not self.cur_category == WMainForm.FAVOURITE_GROUP:
                        chli.setProperty('commands', str2("{0}".format(MenuForm.CMD_ADD_FAVOURITE)))
                    else:
                        cmds = [MenuForm.CMD_MOVE_FAVOURITE,
                                MenuForm.CMD_DEL_FAVOURITE,
                                MenuForm.CMD_DOWN_FAVOURITE,
                                MenuForm.CMD_UP_FAVOURITE]
                        if ch.pin():
                            cmds.append(MenuForm.CMD_SET_FALSE_PIN)
                        else:
                            cmds.append(MenuForm.CMD_SET_TRUE_PIN)
                        chli.setProperty('commands', str2(','.join(cmds)))
                    self.list.addItem(chli)

                except Exception as e:
                    log.e("fillChannels error: {0}".format(uni(e)))
        self.hideStatus()
#         if self.selitem_id < 1:
        self.selitem_id = self.get_selitem_id(self.cur_channel)

    def setLogo(self, ch, chli, sema):

        def set_logo():
            with sema:
                chli.setArt({"icon": str2(ch.logo())})
                chli.setProperty("icon", str2(ch.logo()))

        if not defines.isCancel():
            slthread = threading.Thread(target=set_logo)
            slthread.name = 'thread_set_logo'
            slthread.daemon = False
            slthread.start()

    def fillCategory(self):

        def AddItem(groupname):
            li = xbmcgui.ListItem(str2(self.channel_groups[groupname]['title']))
            li.setProperty('type', 'category')
            li.setProperty('id', str2('{0}'.format(groupname)))
            self.list.addItem(li)

        for name in iterkeys(self.timers):
            if name.startswith(__name__):
                self.timers.stop(name)

        if self.rotate_screen_thr:
            self.rotate_screen_thr.stop()
        if not self.list:
            self.showStatus("Список не инициализирован")
            return
        log.d('fillCategory: Clear list')
        self.list.reset()
        self.list_type = 'groups'
        for gr in self.channel_groups.getGroups():
            if defines.isCancel():
                return
            AddItem(gr)

        if self.list.size() > 0:
            self.setFocus(self.list)
            self.list.selectItem(0)

    def close(self):
        defines.closeRequested.set()
        if self.player:
            self.player.close()
            if self.player._player:
                self.player._player.end()

        for name in iterkeys(self.timers):
            self.timers.stop(name)

        if self.rotate_screen_thr:
            self.rotate_screen_thr.stop()

        if self.loop_play_thr:
            self.loop_play_thr.stop()

        if self._yatv_instance:
            self._yatv_instance.cancel()

        xbmcgui.WindowXML.close(self)

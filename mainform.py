# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import datetime
import json
import threading
import xbmcgui
import xbmc
import time
from pathlib import Path
from operator import methodcaller
from collections import UserDict
import defines
import favdb
import logger
import utils
from epgs.epglist import Epg
from menu import MenuForm
from playerform import MyPlayer
from sources.tchannel import TChannel, MChannel
from sources.table import channel_sources
from sources.channel_info import ChannelInfo


log = logger.Logger(__name__)


class ChannelGroups(UserDict):
    """
    :return {
            groupname: {
                title=str,
                channels=[mchannel,...]
            }
    }
    """

    def __init__(self, *args, **kwargs):
        UserDict.__init__(self, *args, **kwargs)
        self.chinfo = ChannelInfo.get_instance()

    def addGroup(self, groupname, title=None):
        self[groupname] = {'title': title if title else groupname}
        self.clearGroup(groupname)

    def clearGroup(self, groupname):
        self[groupname]['channels'] = []

    def clearGroups(self):
        [self.delGroup(gr) for gr in self.getGroups()]

    def delGroup(self, groupname):
        del self[groupname]

    def getGroups(self):
        return list(self)

    def addChannels(self, channels, src_name):
        [self.addChannel(ch, src_name) for ch in channels]
        return True if channels else False

    def addChannel(self, ch, src_name, groupname=None):
        try:
            if groupname is None:
                groupname = ch.group()
            if groupname is None:
                groupname = src_name
            grinfo = self.chinfo.get_group_by_name(groupname)
            if grinfo and not grinfo['group_enable']:
                return
            if groupname.lower() in ["18+"] and utils.str2int(defines.AGE) < 2:
                return
            log.d(f"addChannel {groupname}/{ch.name()} from source: {src_name}")
            if groupname not in self:
                self.addGroup(groupname)
            src_index = channel_sources.index_by_name(src_name)
            c = next(self.find_channel_by_title(groupname, ch.title()), None)
            if c:
                c.insert(src_index, ch)
            else:
                if not isinstance(ch, MChannel):
                    self.getChannels(groupname).append(MChannel({src_index: ch}))
                else:
                    self.getChannels(groupname).append(ch)
        except Exception as e:
            log.error(f"addChannel from source:{src_name} error: {e}")

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
        return (ch for ch in self.getChannels(groupname) if ch.id() == chid)

    def find_group_by_name(self, name):
        for groupname in (x for x in self.getGroups() if x not in (WMainForm.FAVOURITE_GROUP, WMainForm.SEARCH_GROUP)):
            if next(self.find_channel_by_name(groupname, name), None):
                yield groupname

    def find_group_by_chtitle(self, chtitle):
        for groupname in (x for x in self.getGroups() if x not in (WMainForm.FAVOURITE_GROUP, WMainForm.SEARCH_GROUP)):
            if next(self.find_channel_by_title(groupname, chtitle), None):
                yield groupname

    def find_channel_by_name(self, groupname, name):
        return (ch for ch in self.getChannels(groupname) if ch.name().lower() == name.lower())

    def find_channel_by_title(self, groupname, title):
        return (ch for ch in self.getChannels(groupname) if title.lower() in ch.title().lower())


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
                if self.active and screen:
                    self.img_control.setImage(screen)
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
        self.starttime = 0
        self.name = 'LoopPlay'

    def stop(self):
        log.d("stop from {0}".format(self.name))
        self.active = False
        self.parent.player.channelStop()

    def run(self):
        self.active = True
        while self.active and not defines.isCancel() and (time.time() - self.starttime) > 60:
            try:
                selItem = self.parent.list.getListItem(self.parent.selitem_id)
                if selItem and selItem.getProperty('type') == "channel":
                    self.parent.cur_channel = selItem.getProperty('title')
                    sel_ch = self.parent.get_channel_by_title(self.parent.cur_channel)
                    if not sel_ch:
                        msg = "Канал временно не доступен"
                        self.parent.showStatus(msg)
                        raise Exception(f"{msg}. Возможно не все каналы загрузились...")
                    if not sel_ch.enabled():
                        msg = "Канал отключен пользователем"
                        xbmcgui.Dialog().notification(heading='Запрещено', message=msg)
                        self.stop()
                        break

                    defines.ADDON.setSetting('cur_category', self.parent.cur_category)
                    defines.ADDON.setSetting('cur_channel', self.parent.cur_channel)
                    # defence from loop
                    self.starttime = time.time()
                    if not self.parent.player.Start(sel_ch):
                        break
                    self.parent.player.close()
                if not defines.isCancel():
                    xbmc.sleep(223)
                    self.parent.select_channel()

            except Exception as e:
                log.e(f'LoopPlay error: {e}')
            finally:
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
    NAVIGATE_ACTIONS = (1, 2, 3, 4, 5, 6, 159, 160)
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
        self.player = MyPlayer("player.xml", defines.ADDON_PATH)
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
        self._epgtv_instance = None

    def onInit(self):
        log.d('onInit')
        self.cur_category = defines.ADDON.getSetting('cur_category')
        self.cur_channel = defines.ADDON.getSetting('cur_channel')
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
            if li.getProperty('title') == title:
                return index
        else:
            return -1

    def get_channel_by_title(self, chtitle):
        categ = self.cur_category
        if self.cur_category in (WMainForm.FAVOURITE_GROUP, WMainForm.SEARCH_GROUP):
            categ = next(self.channel_groups.find_group_by_chtitle(chtitle), None)
        return next(self.channel_groups.find_channel_by_title(categ, chtitle), None)

    def showDialog(self, msg):
        from okdialog import OkDialog
        dialog = OkDialog("dialog.xml", defines.ADDON_PATH)
        dialog.setText(msg)
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

                sel_ch = self.get_channel_by_title(selItem.getProperty("title"))
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
                log.d(f'loadFavourites error: {e}')

    def loadSearch(self, *args):
        self.timers.stop(WMainForm.TIMER_HIDE_WINDOW)
        self.channel_groups.clearGroup(WMainForm.SEARCH_GROUP)
        if len(args) > 0:
            chtitle = args[0]
        else:
            chtitle = xbmcgui.Dialog().input(heading='введите название канала')
        log.d(chtitle)
        if chtitle:
            for gr in self.channel_groups.find_group_by_chtitle(chtitle):
                for ch in self.channel_groups.find_channel_by_title(gr, chtitle):
                    try:
                        self.channel_groups.addChannel(ch, src_name='search', groupname=WMainForm.SEARCH_GROUP)
                    except Exception as e:
                        log.d(f'loadSearch error: {e}')

    def loadChannels(self, *args):
        src_name = args[0]
        log.d(f'loadChannels {src_name}')
        src = channel_sources.get_by_name(src_name)
        try:
            res = self.channel_groups.addChannels(src.get_channels(), src_name=src_name)
            timeout = src.reload_interval if res else 60
            if timeout > 0:
                name = f'reload_channels_{src_name}'
                self.timers.stop(name)
                self.timers.start(name, threading.Timer(timeout, self.loadChannels, args=args))

        except Exception as e:
            log.d(f'loadChannels {src_name} error: {e}')

    def getEpg(self, ch, timeout=0, callback=None):
        chnum = self.player.channel_number

        def get():

            try:
                epg = None
                log.d('getEpg->get')
                self.showStatus('Загрузка программы')
                if ch:
                    epg = ch.epg()
                    if callable(callback) and chnum == self.player.channel_number:
                        callback(ch, epg)
                    self.getEpg(ch, 60, callback)
            except Exception as e:
                log.d(f'getEpg->get error: {e}')
            finally:
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
                    ce.setLabel(f"{bt:%H:%M} - {et:%H:%M} {ep['name']}")
                    if i == 0:
                        if self.progress:
                            self.progress.setPercent((ctime - bt).seconds * 100 // (et - bt).seconds)
                        if 'event_id' in ep and not('screens' in ep or 'desc' in ep):
                            ep.update(Epg().link.get_event_info(ep['event_id']))

                        if 'screens' in ep:
                            self.showScreen(ep['screens'], 1)
                        if self.description_label and 'desc' in ep:
                            self.description_label.setText(ep['desc'])
                except:
                    break

            return True

        except Exception as e:
            log.e(f'showEpg error {e}')

    def showNoEpg(self):
        for i in range(99):
            try:
                ce = self.getControl(WMainForm.LBL_FIRST_EPG + i)
                ce.setLabel('')
                if i == 0:
                    ce.setLabel('Нет программы')
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
            for cat, val in self.channel_groups.items():
                for ch in val['channels']:
                    namedb[ch.name().lower()] = {'cat': cat}
                    break
            s = json.dumps(namedb, indent=4, ensure_ascii=False)
            Path(defines.CACHE_PATH, 'namedb.json').write_text(s)

        def LoadOther():
            for name, thr in thrs.items():
                if name not in ('epgtv_epg',):
                    thr.join(60)

        #             dump_channel_groups()

        self.showStatus("Получение списка каналов")

        for groupname in (WMainForm.SEARCH_GROUP, WMainForm.FAVOURITE_GROUP):
            title = '[COLOR FFFFFF00][B]' + groupname + '[/B][/COLOR]'
            self.channel_groups.addGroup(groupname, title)

        thrs = {'favourite': defines.MyThread(self.loadFavourites),
                'epgtv_epg': defines.MyThread(lambda: setattr(self, '_epgtv_instance', Epg().link))}

        thrs.update({src.name: defines.MyThread(self.loadChannels, src.name) for src in channel_sources})

        for thr in thrs.values():
            thr.start()

        lo_thr = defines.MyThread(LoadOther)
        lo_thr.start()

        log.d('Ожидание результата')
        if self.cur_category == WMainForm.FAVOURITE_GROUP:
            thrs['favourite'].join(20)
        else:
            lo_thr.join(len(thrs) * 60)

        if self.cur_category == WMainForm.SEARCH_GROUP:
            self.loadSearch(self.cur_channel)

        self.loadList()

    def loadList(self):
        if self.cur_category == '' or self.cur_category not in self.channel_groups.getGroups():
            self.fillCategory()
        else:
            self.fillChannels()
            if self.init:
                self.select_channel(self.player.channel_number)
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

    def select_channel(self, sch=0, timeout=0):

        def clear():
            self.channel_number_str = ''

        if not self.list_type == 'channels':
            return
        if self.channel_number_str == '':
            self.channel_number_str = str(sch) if sch != 0 else str(self.selitem_id)
        log(f'CHANNEL NUMBER IS: {self.channel_number_str}')
        chnum = utils.str2int(self.channel_number_str)

        if 0 < chnum < self.list.size():
            self.selitem_id = chnum
            self.setFocus(self.list)
            self.list.selectItem(self.selitem_id)

        self.timers.stop(WMainForm.TIMER_SEL_CHANNEL)
        self.timers.start(WMainForm.TIMER_SEL_CHANNEL, threading.Timer(timeout, clear))

    def hide_main_window(self, timeout=0):
        log.d(f'hide main window in {timeout} sec')

        def isPlaying():
            return not defines.isCancel() and self.player._player and self.player._player.isPlaying()

        def hide():
            log.d(f'isPlaying={isPlaying()}')
            if isPlaying():
                for name in self.timers:
                    if name.startswith(__name__):
                        self.timers.stop(name)

                if self.rotate_screen_thr:
                    self.rotate_screen_thr.stop()
                log.d('hide main window')
                self.player.Show()

        self.timers.stop(WMainForm.TIMER_HIDE_WINDOW)
        self.timers.start(WMainForm.TIMER_HIDE_WINDOW, threading.Timer(timeout, hide))

    def add_recent_channel(self, channel, timeout=0):
        log.d(f'add_resent_channel in {timeout} sec')

        def add():
            if not self.cur_category == WMainForm.FAVOURITE_GROUP:
                if favdb.LocalFDB().add_recent(channel.title()):
                    self.channel_groups.clearGroup(WMainForm.FAVOURITE_GROUP)
                    self.loadFavourites()

        self.timers.stop(WMainForm.TIMER_ADD_RECENT)
        self.timers.start(WMainForm.TIMER_ADD_RECENT, threading.Timer(timeout, add))

    def onClick(self, controlID):
        log.d(f'onClick {controlID}')
        if controlID == 200:
            self.setFocusId(WMainForm.CONTROL_LIST)
            self.player.manualStop()
        elif controlID == WMainForm.CONTROL_LIST:
            selItem = self.list.getSelectedItem()

            if not selItem:
                return
            log.d(f"selItem is {selItem.getLabel()}")

            if selItem.getLabel() == '..':
                self.fillCategory()
                return

            if WMainForm.SEARCH_GROUP in selItem.getLabel():
                self.loadSearch()

            if selItem.getProperty('type') == 'category':
                self.cur_category = selItem.getProperty("name")
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
        li = self.getFocus().getSelectedItem()
        if li.getProperty('name') in ['..', WMainForm.FAVOURITE_GROUP, WMainForm.SEARCH_GROUP]:
            return
        mnu = MenuForm(li=li, parent=self)
        selitemid = self.list.getSelectedPosition()

        log.d('Выполнить команду')
        mnu.show()
        log.d('Комманда выполнена')
        res = mnu.GetResult()
        log.d(f'Результат команды {res}')
        if res.startswith('OK'):
            self.channel_groups.delGroup(self.cur_category)
            self.updateList()

#             self.channel_groups.clearGroup(WMainForm.FAVOURITE_GROUP)
#             fthr = defines.MyThread(self.loadFavourites)
#             fthr.start()
#             if self.cur_category == WMainForm.FAVOURITE_GROUP:
#                 fthr.join(10)
#                 self.loadList()

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
        # log.d('Событие {0}'.format(action.getId()))

        if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_BACKSPACE, xbmcgui.ACTION_PARENT_DIR):
            selItem = self.list.getListItem(0)
            if selItem and selItem.getLabel() == "..":
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
            elif action in WMainForm.NAVIGATE_ACTIONS:
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
                self.channel_number_str += str(action.getId() - 58)
                self.select_channel(timeout=1)
            else:
                super(WMainForm, self).onAction(action)

            self.hide_main_window(timeout=10)

    def showStatus(self, text):
        try:
            log.d(f"showStatus: {text}")
            if self.img_progress:
                self.img_progress.setVisible(True)
            if self.txt_progress:
                self.txt_progress.setLabel(text)
        except Exception as e:
            log.w(f"showStatus error: {e}")

    def hideStatus(self):
        try:
            if self.img_progress:
                self.img_progress.setVisible(False)
            if self.txt_progress:
                self.txt_progress.setLabel("")
        except Exception as e:
            log.w(f"hideStatus error: {e}")

    def fillChannels(self):
        self.showStatus("Заполнение списка")
        if not self.list:
            self.showStatus("Список не инициализирован")
            return
        log.d('fillChannels: Clear list')
        self.list.reset()
        self.list_type = 'channels'
        li = xbmcgui.ListItem('..')
        li.setProperty('name', li.getLabel())
        self.list.addItem(li)
        i = 0
        for ch in self.channel_groups.getSortedChannels(self.cur_category):
            if ch:
                try:
                    if defines.isCancel():
                        return
#                     log.d(f'fillChannels add: {ch.title()}')
                    i += 1
                    chli = xbmcgui.ListItem(f"{i}. {ch.title()}")
                    self.setLogo(ch, chli, self.set_logo_sema)
                    chli.setProperties({'type': 'channel', "name": ch.name(), "title": ch.title()})
                    cmds = []

                    if not self.cur_category == WMainForm.FAVOURITE_GROUP:
                        cmds.append(MenuForm.CMD_ADD_FAVOURITE)
                    else:
                        cmds = [MenuForm.CMD_MOVE_FAVOURITE,
                                MenuForm.CMD_DEL_FAVOURITE,
                                MenuForm.CMD_DOWN_FAVOURITE,
                                MenuForm.CMD_UP_FAVOURITE]
                        if ch.pin():
                            cmds.append(MenuForm.CMD_SET_FALSE_PIN)
                        else:
                            cmds.append(MenuForm.CMD_SET_TRUE_PIN)

                    if not ch.enabled():
                        chli.setLabel(f'[COLOR 0xFF555555]{chli.getLabel()}[/COLOR]')
                        cmds.append(MenuForm.CMD_ENABLE_CHANNEL)
                    else:
                        cmds.append(MenuForm.CMD_DISABLE_CHANNEL)

                    chli.setProperty('commands', ','.join(cmds))
                    self.list.addItem(chli)

                except Exception as e:
                    log.e(f"fillChannels error: {e}")
        self.hideStatus()
        self.selitem_id = self.get_selitem_id(self.cur_channel)

    def setLogo(self, ch, chli, sema):

        def set_logo():
            with sema:
                chli.setArt({"icon": ch.logo()})
                chli.setProperty("icon", ch.logo())

        if not defines.isCancel():
            slthread = threading.Thread(target=set_logo)
            slthread.name = 'thread_set_logo'
            slthread.daemon = False
            slthread.start()

    def fillCategory(self):

        def AddItem(groupname):
            li = xbmcgui.ListItem(self.channel_groups[groupname]['title'])
            li.setProperties({'type': 'category', 'name': groupname})
            self.list.addItem(li)

        for name in self.timers:
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
        [AddItem(gr) for gr in self.channel_groups.getGroups()]

        if self.list.size() > 0:
            self.setFocus(self.list)
            self.list.selectItem(0)

    def close(self):
        defines.closeRequested.set()
        if self.player:
            self.player.close()
            if self.player._player:
                self.player._player.end()

        for name in self.timers:
            self.timers.stop(name)

        if self.rotate_screen_thr:
            self.rotate_screen_thr.stop()

        if self.loop_play_thr:
            self.loop_play_thr.stop()

        xbmcgui.WindowXML.close(self)

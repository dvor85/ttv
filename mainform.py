# -*- coding: utf-8 -*-
# Copyright (c) 2013 Torrent-TV.RU
# Writer (c) 2013, Welicobratov K.A., E-mail: 07pov23@gmail.com
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

# imports
import defines
import xbmcgui
import xbmc

import datetime
import threading

from player import MyPlayer
from adswnd import AdsForm
from menu import MenuForm
from infoform import InfoForm
from sources.table import Channels as ChannelSources
import favdb
import json
import re
import utils
from UserDict import UserDict
import logger
import xmltv


log = logger.Logger(__name__)
fmt = utils.fmt


class ChannelGroups(UserDict):
    """
    ChannelGroups = {
        groupname: {
            title=str,
            channels=[[{}...]...]
        }
    }
    """

    def __init__(self):
        self.data = {}

    def setGroup(self, groupname, grouptitle):
        groupname = utils.utf(groupname)
        grouptitle = utils.utf(grouptitle)
        self.data[groupname] = {"title": grouptitle}
        self.clearGroup(groupname)

    def clearGroup(self, groupname):
        groupname = utils.utf(groupname)
        self.data[groupname]['channels'] = []

    def delGroup(self, groupname):
        groupname = utils.utf(groupname)
        del self.data[groupname]

    def getGroups(self):
        return self.data.keys()

    def setChannels(self, channels):
        for ch in channels:
            self.addChannel(ch)

    def addChannel(self, ch, groupname=None):
        try:
            if groupname is None:
                groupname = utils.utf(ch.get('cat'))
            cat = self.data.get(groupname)
            if not cat:
                self.setGroup(groupname, groupname)
            chs = self.find_channel_by_name(groupname, ch.get_name())
            if chs:
                chs.append(ch)
            else:
                self.getChannels(groupname).append([ch])
        except Exception as e:
            log.error(fmt("addChannel error: {0}", e))

    def getChannels(self, groupname):
        groupname = utils.utf(groupname)
        if self.data.get(groupname):
            return self.data[groupname].get("channels")
        else:
            return []

    def find_channel_by_id(self, groupname, chid):
        for chs in self.getChannels(groupname):
            for c in chs:
                if c.get_id() == utils.utf(chid):
                    return chs

    def find_group_by_chname(self, chname):
        name = utils.utf(chname)
        for groupname in (x for x in self.getGroups() if x not in (WMainForm.CHN_TYPE_FAVOURITE)):
            if self.find_channel_by_name(groupname, name):
                return groupname

    def find_channel_by_name(self, groupname, name):
        name = utils.utf(name)
        for chs in self.getChannels(groupname):
            for c in chs:
                if c.get_name().lower().strip() == name.lower().strip():
                    return chs


class RotateScreen(threading.Thread):

    def __init__(self, img_control, screens):
        threading.Thread.__init__(self)
        self.active = False
        self.img_control = img_control
        self.screens = screens
        self.daemon = False

    def run(self):
        self.active = True
        while self.active:
            for screen in self.screens:
                if self.active:
                    self.img_control.setImage(screen['filename'])
                    for i in range(16):  # @UnusedVariable
                        if self.active:
                            xbmc.sleep(100)

    def stop(self):
        self.active = False
        self.img_control.setImage('')


class WMainForm(xbmcgui.WindowXML):
    CANCEL_DIALOG = (9, 10, 11, 92, 216, 247, 257, 275, 61467, 61448,)
    CONTEXT_MENU_IDS = (117, 101)
    ARROW_ACTIONS = (1, 2, 3, 4)
    DIGIT_BUTTONS = range(58, 68)
    ACTION_MOUSE = 107
    BTN_VOD_ID = 113
    BTN_CLOSE = 101
    BTN_FULLSCREEN = 208
    IMG_SCREEN = 210
    IMG_LOGO = 1111
    CONTROL_LIST = 50
    PANEL_ADS = 105

    TXT_PROGRESS = 107
    IMG_PROGRESS = 108
    PROGRESS_BAR = 110

    BTN_INFO = 209
    LBL_FIRST_EPG = 300

    CHN_TYPE_FAVOURITE = 'Избранное'
    CHN_TYPE_MODERATION = 'На модерации'

    API_ERROR_INCORRECT = 'incorrect'
    API_ERROR_NOCONNECT = 'noconnect'
    API_ERROR_ALREADY = 'already'
    API_ERROR_NOPARAM = 'noparam'
    API_ERROR_NOFAVOURITE = 'nofavourite'

    def __init__(self, *args, **kwargs):
        log.d('__init__')
        self.channel_groups = ChannelGroups()
        self._re_1ttv_epg_text = re.compile('var\s+epg\s*=\s*(?P<e>\[.+?\])\s*;.*?</script>', re.DOTALL)
        self._re_1ttv_epg_json = re.compile('(?P<k>\w+)\s*:\s*(?P<v>.+?[,}])')
        self._re_url_match = re.compile('^(?:https?|ftps?|file)://')
        self.archive = []
        self.img_progress = None
        self.txt_progress = None
        self.progress = None
        self.list = None
        self.player = MyPlayer("player.xml", defines.SKIN_PATH, defines.ADDON.getSetting('skin'))
        self.player.parent = self
        self.amalkerWnd = AdsForm("adsdialog.xml", defines.SKIN_PATH, defines.ADDON.getSetting('skin'))
        self.load_selitem_info()
        self.user = None
        self.infoform = None
        self.first_init = True
        self.session = None
        self.channel_number_str = ''

        self.select_timer = None
        self.hide_window_timer = None
        self.get_epg_timer = None
        self.show_screen_timer = None
        self.rotate_screen_thr = None
        defines.MyThread(xmltv.XMLTV.get_instance).start()

    def onInit(self):
        self.img_progress = self.getControl(WMainForm.IMG_PROGRESS)
        self.txt_progress = self.getControl(WMainForm.TXT_PROGRESS)
        self.progress = self.getControl(WMainForm.PROGRESS_BAR)
        self.list = self.getControl(WMainForm.CONTROL_LIST)
        self.init = True

        if not self.channel_groups:
            self.updateList()
        else:
            self.loadList()
        self.hide_main_window(timeout=10)

    def showDialog(self, msg):
        from okdialog import OkDialog
        dialog = OkDialog(
            "okdialog.xml", defines.SKIN_PATH, defines.ADDON.getSetting('skin'))
        dialog.setText(msg)
        dialog.doModal()

    def onFocus(self, ControlID):
        if self.rotate_screen_thr:
            self.rotate_screen_thr.stop()

        for controlId in (WMainForm.IMG_LOGO, WMainForm.IMG_SCREEN):
            self.getControl(controlId).setImage('')

        self.showNoEpg()
        if ControlID == WMainForm.CONTROL_LIST:
            if not self.list:
                return
            selItem = self.list.getSelectedItem()
            if selItem and not selItem.getLabel() == '..':
                sel_chs = self.channel_groups.find_channel_by_name(self.cur_category, selItem.getProperty("name"))
                if sel_chs:
                    self.getEpg(sel_chs, timeout=0.3)
                    self.showScreen(sel_chs, timeout=0.3)

                for controlId in (WMainForm.IMG_LOGO, WMainForm.IMG_SCREEN):
                    self.getControl(controlId).setImage(selItem.getProperty('icon'))

    def load_selitem_info(self):
        self.cur_category = defines.ADDON.getSetting('cur_category')
        self.selitem_id = defines.ADDON.getSetting('cur_channel')
        if self.cur_category == '':
            self.cur_category = WMainForm.CHN_TYPE_FAVOURITE

        if self.selitem_id == '':
            self.selitem_id = -1
        else:
            self.selitem_id = utils.str2int(self.selitem_id)

    def loadFavourites(self, *args):
        from interface import Channel
        for ch in favdb.LocalFDB().get():
            try:
                self.channel_groups.addChannel(Channel(ch), groupname=WMainForm.CHN_TYPE_FAVOURITE)
            except Exception as e:
                log.d(fmt('loadFavourites error: {0}', e))

    def loadChannels(self, *args):
        param = args[0]
        log.d(fmt('loadChannels {0}', param))

        if param in ChannelSources:
            try:
                self.channel_groups.setChannels(ChannelSources[param].get_channels())
            except Exception as e:
                log.d(fmt('loadChannels error: {0}', e))

    def getEpg(self, chs, timeout=0):
        def get():
            try:
                epg = None
                log.d('getEpg->get')
                self.showStatus('Загрузка программы')
                for channel in chs:
                    epg = channel.get_epg()
                    if epg is not None:
                        self.showEpg(epg)
                        break

                self.hideStatus()
            except Exception as e:
                log.d(fmt('getEpg->get error: {0}', e))

        if self.get_epg_timer:
            self.get_epg_timer.cancel()
            self.get_epg_timer = None

        self.get_epg_timer = threading.Timer(timeout, get)
        self.get_epg_timer.name = 'getEpg'
        self.get_epg_timer.daemon = False
        self.get_epg_timer.start()

    def showEpg(self, curepg):
        try:
            ctime = datetime.datetime.now()
            for i, ep in enumerate(curepg):
                try:
                    ce = self.getControl(WMainForm.LBL_FIRST_EPG + i)
                    bt = datetime.datetime.fromtimestamp(float(ep['btime']))
                    et = datetime.datetime.fromtimestamp(float(ep['etime']))
                    ce.setLabel(fmt("{0} - {1} {2}",
                                    bt.strftime("%H:%M"), et.strftime("%H:%M"), ep['name'].replace('&quot;', '"')))
                    if self.progress and i == 0:
                        self.progress.setPercent((ctime - bt).seconds * 100 / (et - bt).seconds)
                except:
                    break

            return True

        except Exception as e:
            log.e(fmt('showEpg error {0}', e))

    def showNoEpg(self):
        for i in range(99):
            try:
                ce = self.getControl(WMainForm.LBL_FIRST_EPG + i)
                if i == 0:
                    ce.setLabel('Нет программы')
                else:
                    ce.setLabel('')
            except:
                break
        if self.progress:
            self.progress.setPercent(1)

    def showScreen(self, chs, timeout=0):
        def show():
            log.d('showScreen')
            screens = None
            for channel in chs:
                screens = channel.get_screenshots()
                if screens is not None:
                    break

            if screens:
                if self.rotate_screen_thr:
                    self.rotate_screen_thr.stop()
                    self.rotate_screen_thr.join(0.2)
                    self.rotate_screen_thr = None

                self.rotate_screen_thr = RotateScreen(self.getControl(WMainForm.IMG_SCREEN), screens)
                self.rotate_screen_thr.start()

            self.show_screen_timer = None

        if self.show_screen_timer:
            self.show_screen_timer.cancel()
            self.show_screen_timer = None

        self.show_screen_timer = threading.Timer(timeout, show)
        self.show_screen_timer.name = 'show_screen'
        self.show_screen_timer.daemon = False
        self.show_screen_timer.start()

    def updateList(self):
        def LoadOther():
            for thr in thrs.itervalues():
                thr.join(10)

        self.showStatus("Получение списка каналов")

        for groupname in [WMainForm.CHN_TYPE_FAVOURITE]:
            self.channel_groups.setGroup(groupname, '[COLOR FFFFFF00][B]' + groupname + '[/B][/COLOR]')

        thrs = {}
        thrs['favourite'] = defines.MyThread(self.loadFavourites)
        for extgr in ChannelSources.iterkeys():
            thrs[extgr] = defines.MyThread(self.loadChannels, extgr)

        for thr in thrs.itervalues():
            thr.start()

        lo_thr = defines.MyThread(LoadOther)
        lo_thr.start()

        log.d('Ожидание результата')
        if self.cur_category in (WMainForm.CHN_TYPE_FAVOURITE):
            thrs['favourite'].join(10)
        else:
            lo_thr.join(20)

        self.loadList()

    def loadList(self):
        log.i('loadList: Clear list')
        self.list.reset()
        self.fillChannels()
        if self.init:
            self.select_channel()
            self.init = False
        if (self.list) and (0 < self.selitem_id < self.list.size()):
            if self.first_init:  # автостарт канала
                self.first_init = False
                self.startChannel()
        self.hideStatus()

    def startChannel(self):
        self.select_channel()
        self.LoopPlay()

    def select_channel(self, sch='', timeout=0):
        def clear():
            self.channel_number_str = ''
            self.select_timer = None

        if self.channel_number_str == '':
            self.channel_number_str = str(
                sch) if sch != '' else str(self.selitem_id)
        chnum = utils.str2int(self.channel_number_str)
        log('CHANNEL NUMBER IS: %i' % chnum)
        if 0 < chnum < self.list.size():
            self.selitem_id = chnum
            self.setFocus(self.list)
            self.list.selectItem(self.selitem_id)

        if self.select_timer:
            self.select_timer.cancel()
            self.select_timer = None
        self.select_timer = threading.Timer(timeout, clear)
        self.select_timer.name = 'select_channel'
        self.select_timer.daemon = False
        self.select_timer.start()

    def hide_main_window(self, timeout=0):
        log.d(fmt('hide main window in {0} sec', timeout))

        def isPlaying():
            return not self.IsCanceled() and self.player.TSPlayer and self.player.TSPlayer.isPlaying()

        def hide():
            log.d(fmt('isPlaying={0}', isPlaying()))
            if isPlaying():
                log.d('hide main window')
                self.player.Show()
            self.hide_window_timer = None

        if self.hide_window_timer:
            self.hide_window_timer.cancel()
            self.hide_window_timer = None

        self.hide_window_timer = threading.Timer(timeout, hide)
        self.hide_window_timer.name = 'hide_main_window'
        self.hide_window_timer.daemon = False
        self.hide_window_timer.start()

    def LoopPlay(self, *args):
        self.source_index = 0
        while not self.IsCanceled():
            try:
                selItem = self.list.getListItem(self.selitem_id)
                categ = self.cur_category
                if categ in (WMainForm.CHN_TYPE_FAVOURITE):
                    categ = self.channel_groups.find_group_by_chname(selItem.getProperty("name"))

                sel_chs = self.channel_groups.find_channel_by_name(categ, selItem.getProperty("name"))
                if not sel_chs:
                    msg = "Канал временно не доступен"
                    self.showStatus(msg)
                    raise Exception(fmt("{msg}. Возможно не все каналы загрузились...", msg=msg))
                if self.source_index >= len(sel_chs):
                    self.source_index = 0

                sel_ch = sel_chs[self.source_index]

                defines.ADDON.setSetting('cur_category', self.cur_category)
                defines.ADDON.setSetting('cur_channel', str(self.selitem_id))

                self.player.Start(selItem.getLabel(), sel_ch)

                if self.player.TSPlayer.manual_stopped:
                    break
                if not self.IsCanceled():
                    xbmc.sleep(223)
                    self.select_channel()

            except Exception as e:
                log.e(fmt('LoopPlay error: {0}', e))
                self.source_index += 1
                xbmc.sleep(1000)

        self.player.close()

        if xbmc.getCondVisibility("Window.IsVisible(home)"):
            log.d("Close from HOME Window")
            self.close()
        elif xbmc.getCondVisibility("Window.IsVisible(video)"):
            self.close()
            log.d("Is Video Window")
        elif xbmc.getCondVisibility("Window.IsVisible(programs)"):
            self.close()
            log.d("Is programs Window")
        elif xbmc.getCondVisibility("Window.IsVisible(addonbrowser)"):
            self.close()
            log.d("Is addonbrowser Window")
        elif xbmc.getCondVisibility("Window.IsVisible(12345)"):
            self.close()
            log.d("Is plugin Window")
        else:
            jrpc = json.loads(xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"GUI.GetProperties","params":{"properties":["currentwindow"]},"id":1}'))
            if jrpc["result"]["currentwindow"]["id"] == 10025:
                log.d("Is video plugins window")
                self.close()

    def onClick(self, controlID):
        log.d('onClick %s' % controlID)
        if controlID == 200:
            self.setFocusId(WMainForm.CONTROL_LIST)
        elif controlID == WMainForm.CONTROL_LIST:
            selItem = self.list.getSelectedItem()

            if not selItem:
                return
            log.d(fmt("selItem is {0}", selItem.getLabel()))
            if selItem.getLabel() == '..':
                self.fillCategory()
                return

            if selItem.getProperty('type') == 'category':
                self.cur_category = selItem.getProperty("id")
                self.selitem_id = -1
                self.fillChannels()
                return

            self.selitem_id = self.list.getSelectedPosition()
            self.LoopPlay()

        elif controlID == WMainForm.BTN_FULLSCREEN:
            self.player.Show()

        elif controlID == WMainForm.BTN_INFO:
            self.showInfoWindow()
            return

    def showInfoWindow(self):
        self.infoform = InfoForm("inform.xml", defines.SKIN_PATH, defines.ADDON.getSetting('skin'))
        self.infoform.parent = self
        self.infoform.doModal()
        self.infoform = None

    def showMenuWindow(self):
        mnu = MenuForm("menu.xml", defines.SKIN_PATH, defines.ADDON.getSetting('skin'))
        mnu.li = self.getFocus().getSelectedItem()
        mnu.parent = self

        log.d('Выполнить команду')
        mnu.doModal()
        log.d('Комманда выполнена')
        res = mnu.GetResult()
        log.d('Результат команды %s' % res)
        if res.startswith('OK'):

            self.channel_groups.clearGroup(WMainForm.CHN_TYPE_FAVOURITE)
            fthr = defines.MyThread(self.loadFavourites)
            fthr.start()
            if self.cur_category == WMainForm.CHN_TYPE_FAVOURITE:
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

    def onAction(self, action):
        # log.d(fmt('Событие {0}', action.getId()))
        if action in WMainForm.CANCEL_DIALOG:
            log.d('ACTION CLOSE FORM')
            self.close()

        if not self.IsCanceled():
            if action.getButtonCode() == 61513:
                return
#             elif action.getId() in WMainForm.ARROW_ACTIONS:
#                 self.onFocus(self.getFocusId())
            elif action.getId() in WMainForm.CONTEXT_MENU_IDS and self.getFocusId() == WMainForm.CONTROL_LIST:
                if action.getId() == 101:
                    return
                self.showMenuWindow()

            elif action.getId() == WMainForm.ACTION_MOUSE:
                if (self.getFocusId() == WMainForm.CONTROL_LIST):
                    self.onFocus(WMainForm.CONTROL_LIST)
            elif action.getId() in WMainForm.DIGIT_BUTTONS:
                # IN PRESSING DIGIT KEYS ############ @IgnorePep8
                self.channel_number_str += str(action.getId() - 58)
                self.select_channel(timeout=1)
            else:
                super(WMainForm, self).onAction(action)

            self.hide_main_window(timeout=10)

    def showStatus(self, text):
        log.d("showStatus: %s" % text)
        try:
            if self.img_progress:
                self.img_progress.setVisible(True)
            if self.txt_progress:
                self.txt_progress.setLabel(text)
            if self.infoform:
                self.infoform.printASStatus(text)
        except Exception as e:
            log.w(fmt("showStatus error: {0}", e))

    def showInfoStatus(self, text):
        if self.infoform:
            self.infoform.printASStatus(text)

    def hideStatus(self):
        try:
            if self.img_progress:
                self.img_progress.setVisible(False)
            if self.txt_progress:
                self.txt_progress.setLabel("")
        except Exception as e:
            log.w(fmt("hideStatus error: {0}", e))

    def fillChannels(self):
        self.showStatus("Заполнение списка")
        if not self.list:
            self.showStatus("Список не инициализирован")
            return
        log.d('fillChannels: Clear list')
        self.list.reset()
        if not self.channel_groups.getChannels(self.cur_category):
            self.fillCategory()
            self.hideStatus()
        else:
            li = xbmcgui.ListItem('..')
            self.list.addItem(li)
            for i, chs in enumerate(self.channel_groups.getChannels(self.cur_category)):
                if chs:
                    ch = chs[0]
                    chname = fmt("{0}. {1}", i + 1, ch.get_name())
                    chli = xbmcgui.ListItem(chname, ch.get_id(), ch.get_logo(), ch.get_logo())
                    chli.setProperty("icon", ch.get_logo())
                    chli.setProperty("id", ch.get_id())
                    chli.setProperty("name", ch.get_name())
                    if self.cur_category not in (WMainForm.CHN_TYPE_FAVOURITE):
                        chli.setProperty('commands', "%s" % (MenuForm.CMD_ADD_FAVOURITE))
                    else:
                        chli.setProperty('commands', "%s,%s,%s,%s" % (
                            MenuForm.CMD_MOVE_FAVOURITE,
                            MenuForm.CMD_DEL_FAVOURITE,
                            MenuForm.CMD_DOWN_FAVOURITE,
                            MenuForm.CMD_UP_FAVOURITE))
                    self.list.addItem(chli)
            self.hideStatus()

    def fillCategory(self):
        def AddItem(groupname):
            li = xbmcgui.ListItem(self.channel_groups[groupname]["title"])
            li.setProperty('type', 'category')
            li.setProperty('id', '%s' % groupname)
            self.list.addItem(li)

        if not self.list:
            self.showStatus("Список не инициализирован")
            return
        log.d('fillCategory: Clear list')
        self.list.reset()
        for gr in self.channel_groups.iterkeys():
            AddItem(gr)

    def IsCanceled(self):
        return defines.isCancel()

    def close(self):
        defines.closeRequested.set()
        if self.player.TSPlayer:
            self.player.TSPlayer.end()

        if self.select_timer:
            self.select_timer.cancel()
        if self.hide_window_timer:
            self.hide_window_timer.cancel()
        if self.get_epg_timer:
            self.get_epg_timer.cancel()
        if self.show_screen_timer:
            self.show_screen_timer.cancel()
        if self.rotate_screen_thr:
            self.rotate_screen_thr.stop()

        xbmcgui.WindowXML.close(self)

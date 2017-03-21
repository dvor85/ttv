# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import xbmcgui
import threading
import xbmc
import datetime
import defines
import re
import utils
import logger
import players


log = logger.Logger(__name__)
fmt = utils.fmt


class MyPlayer(xbmcgui.WindowXML):
    CANCEL_DIALOG = (9, 10, 11, 92, 216, 247, 257, 275, 61467, 61448,)
    CONTROL_FIRST_EPG_ID = 109
    CONTROL_PROGRESS_ID = 310
    CONTROL_ICON_ID = 202
    CONTROL_WINDOW_ID = 203
    CONTROL_BUTTON_PAUSE = 204
    CONTROL_BUTTON_INFOWIN = 209
    CONTROL_BUTTON_STOP = 200
    ACTION_RBC = 101
    ARROW_ACTIONS = (1, 2, 3, 4)
    PAGE_UP_DOWN = (5, 6)
    DIGIT_BUTTONS = range(58, 68)
    CH_NAME_ID = 399
    DLG_SWITCH_ID = 299

    TIMER_RUN_SEL_CHANNEL = 'run_selected_channel'
    TIMER_HIDE_CONTROL = 'hide_control_timer'

    def __init__(self, *args, **kwargs):
        log.d('__init__')
        self._player = None
        self.parent = None
        self.channels = None
        self.title = ''
        self.visible = False
        self.focusId = MyPlayer.CONTROL_WINDOW_ID

        self.timers = {}

        self.channel_number = 0
        self.channel_number_str = ''
        self.progress = None
        self.chinfo = None
        self.swinfo = None
        self.control_window = None
        self._re_source = re.compile('(loadPlayer|loadTorrent)\("(?P<src>[\w/_:.]+)"')

    def onInit(self):
        log.d('onInit')
        if not (self.channels and self.parent):
            return
        self.progress = self.getControl(MyPlayer.CONTROL_PROGRESS_ID)
        cicon = self.getControl(MyPlayer.CONTROL_ICON_ID)
        for ch in self.channels.itervalues():
            logo = ch.get_logo()
            if logo:
                cicon.setImage(logo)
                break
        self.control_window = self.getControl(MyPlayer.CONTROL_WINDOW_ID)
        self.chinfo = self.getControl(MyPlayer.CH_NAME_ID)
        self.chinfo.setLabel(self.title)
        self.swinfo = self.getControl(MyPlayer.DLG_SWITCH_ID)
        self.swinfo.setVisible(False)

        if not self.timers.get(MyPlayer.TIMER_RUN_SEL_CHANNEL):
            self.init_channel_number()

        log.d(fmt("channel_number = {0}", self.channel_number))
        log.d(fmt("selitem_id = {0}", self.parent.selitem_id))
        self.UpdateEpg(self.channels)

        self.control_window.setVisible(True)
        self.hide_control_window(timeout=5)

    def init_channel_number(self):
        if self.channel_number != 0:
            self.parent.selitem_id = self.channel_number
        else:
            self.channel_number = self.parent.selitem_id

    def hide_control_window(self, timeout=0):
        def hide():
            self.control_window.setVisible(False)
            self.setFocusId(MyPlayer.CONTROL_WINDOW_ID)
            self.focusId = MyPlayer.CONTROL_WINDOW_ID
            self.timers[MyPlayer.TIMER_HIDE_CONTROL] = None

        if self.timers.get(MyPlayer.TIMER_HIDE_CONTROL):
            self.timers[MyPlayer.TIMER_HIDE_CONTROL].cancel()
            self.timers[MyPlayer.TIMER_HIDE_CONTROL] = None

        if not defines.isCancel():
            self.timers[MyPlayer.TIMER_HIDE_CONTROL] = threading.Timer(timeout, hide)
            self.timers[MyPlayer.TIMER_HIDE_CONTROL].name = MyPlayer.TIMER_HIDE_CONTROL
            self.timers[MyPlayer.TIMER_HIDE_CONTROL].daemon = False
            self.timers[MyPlayer.TIMER_HIDE_CONTROL].start()

    def UpdateEpg(self, chs):
        try:
            log.d('UpdateEpg')

            name = None
            cicon = self.getControl(MyPlayer.CONTROL_ICON_ID)
            for ch in chs.itervalues():
                logo = ch.get_logo()
                name = ch.get_name()
                if logo:
                    cicon.setImage(logo)
                    break

            for ch in self.channels.itervalues():
                try:
                    if ch.get_name() != name:
                        self.showNoEpg()
                    break
                except Exception as e:
                    log.d(fmt("UpdateEpg error: {0}", e))

            self.parent.getEpg(chs, callback=self.showEpg, timeout=0.5)

        except Exception as e:
            log.w(fmt('UpdateEpg error: {0}', e))

    def showEpg(self, curepg):
        try:
            ctime = datetime.datetime.now()
            for i, ep in enumerate(curepg):
                try:
                    ce = self.getControl(MyPlayer.CONTROL_FIRST_EPG_ID + i)
                    bt = datetime.datetime.fromtimestamp(float(ep['btime']))
                    et = datetime.datetime.fromtimestamp(float(ep['etime']))
                    ce.setLabel(fmt("{0} - {1} {2}", bt.strftime("%H:%M"),
                                    et.strftime("%H:%M"), ep['name'].replace('&quot;', '"')))
                    if self.progress and i == 0:
                        self.progress.setPercent((ctime - bt).seconds * 100 / (et - bt).seconds)
                except:
                    break

            return True

        except Exception as e:
            log.e(fmt('showEpg error {0}', e))

        self.showNoEpg()

    def showNoEpg(self):
        for i in range(99):
            try:
                ce = self.getControl(MyPlayer.CONTROL_FIRST_EPG_ID + i)
                if i == 0:
                    ce.setLabel('Нет программы')
                else:
                    ce.setLabel('')
            except:
                break
        if self.progress:
            self.progress.setPercent(0)

    def Stop(self):
        log('AutoStop')
        # xbmc.executebuiltin('PlayerControl(Stop)')
        if self._player:
            self._player.manual_stopped.clear()
            self._player.stop()

    def Show(self):
        if self._player:
            self.show()

    def Start(self, channels):
        log("Start play")
        self.channels = channels
        self.channel_number = self.parent.selitem_id
        for src, channel in self.channels.iteritems():
            try:
                self.title = fmt("{0}. {1}", self.channel_number, channel.get_name())

                for player in channel.get('players'):
                    try:
                        if self._player:
                            self._player.stop()
                        url = channel.get_url(player)
                        mode = channel.get_mode()
                        log.d(fmt('Try to play with {0} player', player))
                        if player == 'ace':
                            self._player = players.AcePlayer.get_instance(parent=self.parent)
                        elif player == 'nox':
                            self._player = players.NoxPlayer.get_instance(parent=self.parent)
                        else:
                            self._player = players.TPlayer.get_instance(parent=self.parent)

                        if self._player and self._player.play_item(index=0, title=self.title,
                                                                   iconImage=channel.get_logo(),
                                                                   thumbnailImage=channel.get_logo(),
                                                                   url=url, mode=mode):
                            log.d('End playing')
                            return True
                    except Exception as e:
                        log.error(fmt("Error play with {0} player: {1}", player, e))
                else:
                    raise Exception(fmt('There are no availible players for "{0}" in source "{1}"', channel.get_name(), src))

                return True
            except Exception as e:
                log.e(fmt('Start error: {0}', e))

    def run_selected_channel(self, timeout=0):
        def run():
            self.channel_number = utils.str2int(self.channel_number_str)
            log.d(fmt('CHANNEL NUMBER IS: {0}', self.channel_number))
            if 0 < self.channel_number < self.parent.list.size() and self.parent.selitem_id != self.channel_number:
                self.parent.selitem_id = self.channel_number
                self.Stop()
            else:
                self.swinfo.setVisible(False)
            self.channel_number = self.parent.selitem_id
            self.chinfo.setLabel(self.parent.list.getListItem(self.parent.selitem_id).getLabel())
            self.channel_number_str = ''
            self.timers[MyPlayer.TIMER_RUN_SEL_CHANNEL] = None

        if self.timers.get(MyPlayer.TIMER_RUN_SEL_CHANNEL):
            self.timers[MyPlayer.TIMER_RUN_SEL_CHANNEL].cancel()
            self.timers[MyPlayer.TIMER_RUN_SEL_CHANNEL] = None

        if not defines.isCancel():
            self.timers[MyPlayer.TIMER_RUN_SEL_CHANNEL] = threading.Timer(timeout, run)
            self.timers[MyPlayer.TIMER_RUN_SEL_CHANNEL].name = MyPlayer.TIMER_RUN_SEL_CHANNEL
            self.timers[MyPlayer.TIMER_RUN_SEL_CHANNEL].daemon = False
            self.timers[MyPlayer.TIMER_RUN_SEL_CHANNEL].start()

    def inc_channel_number(self):
        self.channel_number += 1
        if self.channel_number >= self.parent.list.size():
            self.channel_number = 1

    def dec_channel_number(self):
        self.channel_number -= 1
        if self.channel_number <= 0:
            self.channel_number = self.parent.list.size() - 1

    def onAction(self, action):
        def viewEPG(swinfo_visible=True):
            selItem = self.parent.list.getListItem(self.channel_number)
            self.chinfo.setLabel(selItem.getLabel())
            self.swinfo.setVisible(swinfo_visible)

            sel_chs = self.parent.get_channel_by_name(selItem.getProperty("name"))
            if sel_chs:
                self.UpdateEpg(sel_chs)

        # log.d(fmt('Action {0} | ButtonCode {1}', action.getId(), action.getButtonCode()))
        if action in MyPlayer.CANCEL_DIALOG or action.getId() == MyPlayer.ACTION_RBC:
            log.d(fmt('Close player {0} {1}', action.getId(), action.getButtonCode()))
            if self.timers.get(MyPlayer.TIMER_RUN_SEL_CHANNEL):
                self.channel_number_str = str(self.parent.selitem_id)
                self.run_selected_channel()
                self.UpdateEpg(self.channels)
            else:
                self.close()
        elif action.getId() in (3, 4, 5, 6):
            # IF ARROW UP AND DOWN PRESSED - SWITCH CHANNEL ##### @IgnorePep8
            if action.getId() in (3, 5):
                self.inc_channel_number()
            else:
                self.dec_channel_number()

            self.channel_number_str = str(self.channel_number)
            viewEPG()

            self.run_selected_channel(timeout=5)

        elif action.getId() in MyPlayer.DIGIT_BUTTONS:
            # IF PRESSED DIGIT KEYS - SWITCH CHANNEL ############## @IgnorePep8
            digit_pressed = action.getId() - 58
            if digit_pressed < self.parent.list.size():

                self.channel_number_str += str(digit_pressed)
                self.channel_number = utils.str2int(self.channel_number_str)
                if not 0 < self.channel_number < self.parent.list.size():
                    self.channel_number_str = str(digit_pressed)
                    self.channel_number = utils.str2int(self.channel_number_str)

                viewEPG()

                self.run_selected_channel(timeout=5)
        elif action.getId() == 0 and action.getButtonCode() == 61530:
            xbmc.executebuiltin('Action(FullScreen)')
            xbmc.sleep(4000)
            xbmc.executebuiltin('Action(Back)')
        else:
            self.UpdateEpg(self.channels)

        if not self.visible:
            if self.focusId == MyPlayer.CONTROL_WINDOW_ID:
                self.setFocusId(MyPlayer.CONTROL_BUTTON_PAUSE)
            else:
                self.setFocusId(self.focusId)
            self.setFocusId(self.getFocusId())
            self.control_window.setVisible(True)
            self.hide_control_window(timeout=5)

    def onClick(self, controlID):
        if controlID == MyPlayer.CONTROL_BUTTON_STOP:
            self.close()
        if controlID == self.CONTROL_BUTTON_INFOWIN:
            self.parent.showInfoWindow()

    def close(self):
        for timer in self.timers.itervalues():
            if timer:
                timer.cancel()

        xbmcgui.WindowXML.close(self)

# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import datetime
import threading

import xbmcgui
import xbmc
from six import iteritems, iterkeys
from utils import uni, str2

import defines
import logger
import players
import utils


log = logger.Logger(__name__)


class MyPlayer(xbmcgui.WindowXML):
    CANCEL_DIALOG = (9, 10, 11, 92, 216, 247, 257, 275, 61467, 61448,)
    CONTROL_FIRST_EPG_ID = 109
    CONTROL_PROGRESS_ID = 310
    CONTROL_ICON_ID = 202
    CONTROL_WINDOW_ID = 203
    CONTROL_BUTTON_PAUSE = 204
    CONTROL_BUTTON_NEXT = 209
    CONTROL_BUTTON_STOP = 200
    ACTION_RBC = 101
    ARROW_ACTIONS = (1, 2, 3, 4)
    PAGE_UP_DOWN = (5, 6)
    DIGIT_BUTTONS = list(range(58, 68))
    CH_NAME_ID = 399
    DLG_SWITCH_ID = 299
    PLAYER_WINDOW_ID = 12346

    TIMER_RUN_SEL_CHANNEL = 'run_selected_channel'
    TIMER_HIDE_CONTROL = 'hide_control_timer'

    def __init__(self, xmlFilename, scriptPath, *args, **kwargs):
        super(MyPlayer, self).__init__(xmlFilename, scriptPath)
        log.d('__init__')
        self._player = None
        self.parent = None
        self.channel = None
        self.title = ''
        self.focusId = MyPlayer.CONTROL_WINDOW_ID

        self.timers = defines.Timers()

        self.channel_number = 0
        self.channel_number_str = ''
        self.progress = None
        self.chinfo = None
        self.swinfo = None
        self.cicon = None
        self.control_window = None
        self.visible = threading.Event()

    def onInit(self):
        log.d('onInit')
        if not (self.channel and self.parent):
            return
        self.visible.set()
        self.progress = self.getControl(MyPlayer.CONTROL_PROGRESS_ID)
        self.cicon = self.getControl(MyPlayer.CONTROL_ICON_ID)
        self.cicon.setVisible(False)
        logo = self.channel.logo()
        if logo:
            self.cicon.setVisible(True)

        self.cicon.setImage(str2(logo))
        self.control_window = self.getControl(MyPlayer.CONTROL_WINDOW_ID)
        self.chinfo = self.getControl(MyPlayer.CH_NAME_ID)
        self.chinfo.setLabel(str2(self.title))
        self.swinfo = self.getControl(MyPlayer.DLG_SWITCH_ID)
        self.hideStatus()

        if not self.timers.get(MyPlayer.TIMER_RUN_SEL_CHANNEL):
            self.init_channel_number()

        log.d("channel_number = {0}".format(self.channel_number))
        log.d("selitem_id = {0}".format(self.parent.selitem_id))
        self.UpdateEpg(self.channel)

        self.control_window.setVisible(True)
        self.hide_control_window(timeout=5)

    @property
    def manual_stop_requested(self):
        return players.Flags.manual_stopped.is_set()

    @property
    def switch_source_requested(self):
        return players.Flags.switch_source.is_set()

    @property
    def channel_stop_requested(self):
        return players.Flags.channel_stop.is_set()

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

        self.timers.stop(MyPlayer.TIMER_HIDE_CONTROL)
        self.timers.start(MyPlayer.TIMER_HIDE_CONTROL, threading.Timer(timeout, hide))

    def UpdateEpg(self, ch):
        try:
            log.d('UpdateEpg')
            logo = ch.logo()
            if self.cicon:
                self.cicon.setImage(str2(logo))
            self.parent.getEpg(ch, callback=self.showEpg, timeout=0.5)

        except Exception as e:
            log.w('UpdateEpg error: {0}'.format(uni(e)))

    def showEpg(self, curepg):
        try:
            ctime = datetime.datetime.now()
            if not curepg:
                self.showNoEpg()
                return False
            for i, ep in enumerate(curepg):
                try:
                    ce = self.getControl(MyPlayer.CONTROL_FIRST_EPG_ID + i)
                    bt = datetime.datetime.fromtimestamp(float(ep['btime']))
                    et = datetime.datetime.fromtimestamp(float(ep['etime']))
                    ce.setLabel(str2("{0} - {1} {2}").format(str2(bt.strftime("%H:%M")),
                                                             str2(et.strftime("%H:%M")),
                                                             str2(ep['name'].replace('&quot;', '"'))))
                    if self.progress and i == 0:
                        self.progress.setPercent((ctime - bt).seconds * 100 // (et - bt).seconds)
                except Exception:
                    break

            return True

        except Exception as e:
            log.e('showEpg error {0}'.format(uni(e)))

    def showNoEpg(self):
        for i in range(99):
            try:
                ce = self.getControl(MyPlayer.CONTROL_FIRST_EPG_ID + i)
                if i == 0:
                    ce.setLabel('Нет программы')
                else:
                    ce.setLabel('')
            except Exception:
                break
        if self.progress:
            self.progress.setPercent(0)

    #     def isVisible(self):
    #         return xbmc.getCondVisibility("Window.IsVisible({window})".format(window=MyPlayer.PLAYER_WINDOW_ID))

    def Show(self):
        log.d('Show')
        if self._player:
            self.show()

    def Start(self, channel):
        """
        Start play. Try all availible channel sources and players
        :channel: <dict> TChannel sources
        :return: If channel stop requested, then return True, else None
        """

        log("Start play")
        self.channel = channel
        self.channel_number = self.parent.selitem_id
        try:
            self.title = "{0}. {1}".format(self.channel_number, channel.title())
            if len(channel.xurl()) > 0:
                for src_name, player_url in channel.xurl():
                    for player, url_mode in iteritems(player_url):
                        try:
                            url, mode = url_mode
                            log.d('Try to play with {0} player'.format(player))
                            logo = channel.logo()
                            if self.cicon:
                                self.cicon.setImage(str2(logo))
                            if player == 'ace':
                                if self._player and self._player.last_error:
                                    players.AcePlayer.clear_instance()
                                    self._player = None
                                self._player = players.AcePlayer.get_instance(parent=self.parent)

                            elif player == 'nox':
                                if self._player and self._player.last_error:
                                    players.NoxPlayer.clear_instance()
                                    self._player = None
                                self._player = players.NoxPlayer.get_instance(parent=self.parent)
                            else:
                                if self._player and self._player.last_error:
                                    players.TPlayer.clear_instance()
                                    self._player = None
                                self._player = players.TPlayer.get_instance(parent=self.parent)

                            if self._player:
                                self.parent.add_recent_channel(channel, 300)
                                try:
                                    log.d('play "{0}" from source "{1}"'.format(url, src_name))
                                    self._player.play_item(index=0, title=self.title,
                                                           iconImage=logo,
                                                           thumbnailImage=logo,
                                                           url=url, mode=mode)
                                except Exception as e:
                                    log.e("Error play {0}: {1}".format(url_mode, e))
                                finally:
                                    if self.manual_stop_requested or defines.isCancel():
                                        self.close()
                                        return
                                    if self.channel_stop_requested:
                                        return True
                                log.d('End playing url "{0}"'.format(url_mode))

                        except Exception as e:
                            log.e("Error play with {0} player: {1}".format(player, e))
                        finally:
                            if self.manual_stop_requested or defines.isCancel():
                                self.close()
                                return
                            if self.channel_stop_requested:
                                return True
            else:
                log.notice('Нечего проигрывать!')
                self.manualStop()

        except Exception as e:
            log.e('Start error: {0}'.format(uni(e)))

        if self.manual_stop_requested or defines.isCancel():
            self.close()
            return

        return True

    def run_selected_channel(self, timeout=0):

        def run():
            self.channel_number = utils.str2int(self.channel_number_str)
            log.d('CHANNEL NUMBER IS: {0}'.format(self.channel_number))
            if 0 < self.channel_number < self.parent.list.size() and self.parent.selitem_id != self.channel_number:
                self.parent.selitem_id = self.channel_number
                self.channelStop()
            else:
                self.hideStatus()
            self.channel_number = self.parent.selitem_id
            self.chinfo.setLabel(self.parent.list.getListItem(self.parent.selitem_id).getLabel())
            self.channel_number_str = ''
            self.timers.stop(MyPlayer.TIMER_RUN_SEL_CHANNEL)

        self.timers.stop(MyPlayer.TIMER_RUN_SEL_CHANNEL)
        self.timers.start(MyPlayer.TIMER_RUN_SEL_CHANNEL, threading.Timer(timeout, run))

    def inc_channel_number(self):
        self.channel_number += 1
        if self.channel_number >= self.parent.list.size():
            self.channel_number = 1

    def dec_channel_number(self):
        self.channel_number -= 1
        if self.channel_number <= 0:
            self.channel_number = self.parent.list.size() - 1

    def showStatus(self, text):
        try:
            log.d("showStatus: {0}".format(uni(text)))
            if self.swinfo:
                self.swinfo.setLabel(str2(text))
                self.swinfo.setVisible(True)
        except Exception as e:
            log.w("showStatus error: {0}".format(uni(e)))

    def hideStatus(self):
        try:
            if self.swinfo:
                self.swinfo.setVisible(False)
        except Exception as e:
            log.w("hideStatus error: {0}".format(uni(e)))

    def autoStop(self):
        if self._player:
            self._player.autoStop()
        else:
            players.Flags.autoStop()

    def manualStop(self):
        if self._player:
            self._player.manualStop()
        else:
            players.Flags.manualStop()

    def channelStop(self):
        if self._player:
            self._player.channelStop()
        else:
            players.Flags.channelStop()

    def Stop(self):
        if self._player:
            return self._player.stop()

    def onAction(self, action):

        def viewEPG():
            selItem = self.parent.list.getListItem(self.channel_number)
            if selItem and uni(selItem.getProperty("type")) == 'channel':
                self.chinfo.setLabel(selItem.getLabel())
                self.showStatus('Переключение...')

                sel_ch = self.parent.get_channel_by_title(uni(selItem.getProperty("title")))
                if sel_ch:
                    self.UpdateEpg(sel_ch)
                return True

#         log.d('Action {0} | ButtonCode {1}'.format(action.getId(), action.getButtonCode()))
        if action in MyPlayer.CANCEL_DIALOG or action.getId() == MyPlayer.ACTION_RBC:
            log.d('Close player {0} {1}'.format(action.getId(), action.getButtonCode()))
            if self.timers.get(MyPlayer.TIMER_RUN_SEL_CHANNEL):
                self.channel_number_str = str2(self.parent.selitem_id)
                self.run_selected_channel()
                self.UpdateEpg(self.channel)
            else:
                self.close()

        elif action in (xbmcgui.ACTION_NEXT_ITEM, xbmcgui.ACTION_PREV_ITEM):
            self.autoStop()
        elif action in (xbmcgui.ACTION_STOP, xbmcgui.ACTION_PAUSE):
            self.manualStop()

        elif action in (
                xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_PAGE_UP, xbmcgui.ACTION_PAGE_DOWN):
            # IF ARROW UP AND DOWN PRESSED - SWITCH CHANNEL ##### @IgnorePep8
            if action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_PAGE_UP):
                self.inc_channel_number()
            else:
                self.dec_channel_number()

            self.channel_number_str = str2(self.channel_number)
            if viewEPG():
                self.run_selected_channel(timeout=5)

        elif action.getId() in MyPlayer.DIGIT_BUTTONS:
            # IF PRESSED DIGIT KEYS - SWITCH CHANNEL ############## @IgnorePep8
            digit_pressed = action.getId() - 58
            if digit_pressed < self.parent.list.size():

                self.channel_number_str += str2(digit_pressed)
                self.channel_number = utils.str2int(self.channel_number_str)
                if not 0 < self.channel_number < self.parent.list.size():
                    self.channel_number_str = uni(digit_pressed)
                    self.channel_number = utils.str2int(self.channel_number_str)

                if viewEPG():
                    self.run_selected_channel(timeout=5)
        elif action.getId() == 0 and action.getButtonCode() == 61530:
            xbmc.executebuiltin('Action(FullScreen)')
            xbmc.sleep(4000)
            xbmc.executebuiltin('Action(Back)')
        else:
            self.UpdateEpg(self.channel)

        if not self.visible.is_set():
            if self.focusId == MyPlayer.CONTROL_WINDOW_ID:
                self.setFocusId(MyPlayer.CONTROL_BUTTON_PAUSE)
            else:
                self.setFocusId(self.focusId)

        self.setFocusId(self.getFocusId())
        self.control_window.setVisible(True)
        self.hide_control_window(timeout=5)

    def onClick(self, controlID):
        if controlID == MyPlayer.CONTROL_BUTTON_STOP:
            self.manualStop()
            self.close()
        elif controlID == MyPlayer.CONTROL_BUTTON_NEXT:
            self.autoStop()

    def close(self):
        for name in iterkeys(self.timers):
            self.timers.stop(name)
        if self.visible.is_set():
            xbmcgui.WindowXML.close(self)
        self.visible.clear()

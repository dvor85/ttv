# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import datetime
import threading
import xbmcgui
import xbmc
import re
import requests
from collections import UserDict

import defines
import logger
import players
import utils
from epgs.epgtv import get_name_offset
from sources.tchannel import TChannel
from sources.channel_info import ChannelInfo
from http.server import BaseHTTPRequestHandler
import socketserver

log = logger.Logger(__name__)


class ProxyTV(UserDict):
    #     _re_name_url = re.compile(r'#EXTINF:.*?,(?P<name>.*?)\-.*\<br\>(?P<url>[\w\.\:/]+)\<br\>')
    _re_name_url = re.compile(r'> (?P<prov>[^\<\>]+)<br><div align=\"left\">.+?#EXTINF:.+?,(?P<name>.+?)\-\d+\<br\>(?P<url>[\w\.\:/]+)\<br\>')

    def __init__(self):
        UserDict.__init__(self)
        self.sess = requests.Session()
        self.data = {}

    def search_by_name(self, name):
        name = name.lower()
        log.d(f"search source in proxytv by {name}")
        params = {"udpxyaddr": f"ch:{name}"}
        headers = {'Referer': 'https://proxytv.ru/'}
        if not self.sess.cookies:
            defines.request('https://proxytv.ru/', method='head', session=self.sess, headers=headers)

        r = defines.request('https://proxytv.ru/iptv/php/srch.php', method='post', session=self.sess, params=params, headers=headers)
        if r:
            self.data.setdefault(name, [])
            self.data.setdefault(f'{name} hd', [])
            for p, n, u in ProxyTV._re_name_url.findall(r.text):
                self.data.setdefault(n.lower().strip(), []).append({p: u})


class MyProxyServer(socketserver.ThreadingTCPServer):
    daemon_threads = False
    timeout = 5

    def __init__(self, address, port):
        return super().__init__((address, port), MyProxyHandler)


class MyProxyHandler(BaseHTTPRequestHandler):
    timeout = 5
    buff = 8192

    def do_HEAD(self, **headers):
        self.send_response(200)
        [self.send_header(k, v) for k, v in headers.items()]
        self.end_headers()

    def do_GET(self):
        url = self.path[1:]
        if '://' in url:
            self.do_HEAD(**{'Content-type': 'application/octet-stream'})
            while not (players.Flags.is_any_flag_set() or defines.isCancel()):
                r = defines.request(url, trys=2, stream=True, timeout=self.timeout)
                for data in r.iter_content(self.buff):
                    self.wfile.write(data)
                    self.wfile.flush()


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
    EPG_END_ID = 300
    DLG_SWITCH_ID = 299
    PLAYER_WINDOW_ID = 12346

    TIMER_RUN_SEL_CHANNEL = 'run_selected_channel'
    TIMER_HIDE_CONTROL = 'hide_control_timer'
    TIMER_HIDE_STATUS = 'hide_status'

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
        self.chinfo_label = None
        self.swinfo = None
        self.cicon = None
        self.control_window = None

        self.proxytv = ProxyTV()
        self.visible = threading.Event()
        self.chinfo = ChannelInfo().get_instance()

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
            self.cicon.setImage(logo)
        self.control_window = self.getControl(MyPlayer.CONTROL_WINDOW_ID)
        self.chinfo_label = self.getControl(MyPlayer.CH_NAME_ID)
        self.chinfo_label.setLabel(self.title)
        self.swinfo = self.getControl(MyPlayer.DLG_SWITCH_ID)
        self.hideStatus()

        if not self.timers.get(MyPlayer.TIMER_RUN_SEL_CHANNEL):
            self.init_channel_number()

        log.d(f"channel_number = {self.channel_number}")
        log.d(f"selitem_id = {self.parent.selitem_id}")
        self.UpdateEpg(self.channel)

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

        self.timers.stop(MyPlayer.TIMER_HIDE_CONTROL)
        self.timers.start(MyPlayer.TIMER_HIDE_CONTROL, threading.Timer(timeout, hide))

    def UpdateEpg(self, ch):
        try:
            log.d('UpdateEpg')
            logo = ch.logo()
            if self.cicon:
                self.cicon.setImage(logo)
            self.parent.getEpg(ch, callback=self.showEpg, timeout=0.5)

        except Exception as e:
            log.w(f'UpdateEpg error: {e}')

    def showEpg(self, ch, curepg):
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
                    ce.setLabel(f"{bt:%H:%M} - {et:%H:%M} {ep['name']}")
                    if self.progress and i == 0:
                        self.progress.setPercent((ctime - bt).seconds * 100 // (et - bt).seconds)
                except Exception:
                    break

            return True

        except Exception as e:
            log.e(f'showEpg error {e}')

    def showNoEpg(self):
        for i in range(99):
            try:
                ce = self.getControl(MyPlayer.CONTROL_FIRST_EPG_ID + i)
                ce.setLabel('')
                if i == 0:
                    ce.setLabel('Нет программы')
            except Exception:
                break
        if self.progress:
            self.progress.setPercent(0)

    def Show(self):
        log.d('Show')
        if self._player:
            self.show()

    def get_normal_title(self, name):
        name = get_name_offset(name.lower())[0]
        chinfo = self.chinfo.get_channel_by_name(name)
        return next(filter(bool, (chinfo['ch_title'], chinfo['ch_epg'])), name) if chinfo else name

    def Start(self, channel, **kwargs):
        """
        Start play. Try all availible channel sources and players
        :channel: <dict> MChannel sources
        :return: If channel stop requested, then return
        """

        log("Start play")
        self.channel = channel
        self.channel_number = self.parent.selitem_id
        chli = kwargs.get('chli')
        players.Flags.clear()
        title = self.get_normal_title(channel.title())
        title_wo_hd = title.replace(' hd', '') if title.endswith(' hd') else title
        self.title = f"{self.channel_number}. {channel.title()}"
        while not (players.Flags.channel_stop_requested() or defines.isCancel()):
            for src_name, player_url in channel.xurl().copy():
                for player, url_mode in player_url.items():
                    try:
                        players.Flags.clear()
                        url = url_mode['url']
                        if callable(url):
                            url = url()

                        log.d(f'Try to play {url} with {player} player')

                        logo = channel.logo()
                        if self.cicon:
                            self.cicon.setImage(logo)

                        if self._player and self._player.last_error:
                            self._player.clear_instance()
                            self._player = None

                        if player == 'ace':
                            self._player = players.AcePlayer.get_instance(parent=self.parent)
                        elif player == 'nox':
                            self._player = players.NoxPlayer.get_instance(parent=self.parent)
                        else:
                            self._player = players.TPlayer.get_instance(parent=self.parent)

                        if self._player:
                            self.parent.add_recent_channel(channel, 300)
                            if url_mode.get('availible', True):

                                with defines.progress_dialog_bg(f"Проверка доступности источника для канала {channel.title()}") as pd:
                                    defines.request(url, method='GET', timeout=3, stream=True)
                                    pd.update(100)

                                if url.endswith('.m3u8'):
                                    with defines.progress_dialog(f'Ожидание источника для канала: {channel.title()}.') as pd:
                                        srcs = None
                                        for t in range(5):
                                            r = defines.request(url, trys=2, interval=2)
                                            if r:
                                                srcs = [s for s in r.text.splitlines() if s and not s.startswith('#') and
                                                        not any(ex in s for ex in ('errors', 'promo', 'block'))]

                                                if srcs:
                                                    if src_name not in ('ttv'):
                                                        break
                                                    elif len(srcs) > 2:
                                                        break

                                            for k in range(5):
                                                if pd.iscanceled() or defines.isCancel():
                                                    self.channelStop()
                                                    raise Exception('Waiting for source has been canceled')
                                                defines.monitor.waitForAbort(1.2)
                                                pd.update(4 * (5 * t + k + 1))
                                        log.d(f"sources={srcs}")
                                        if not srcs:
                                            raise ValueError(f'Source "{url}" is not availible. Channel "{channel.title()}" in "{src_name}"')
                                else:
                                    url = f'http://{self.parent.proxy_address}:{self.parent.proxy_port}/{url}'

                                while not (players.Flags.is_any_flag_set() or defines.isCancel()):
                                    log.d(f'play "{url}" from source "{src_name}"')
                                    xbmc.executebuiltin('Dialog.Close(okdialog)')
                                    defines.showNotification(heading='Источник', message=src_name, icon='')
                                    self._player.play_item(index=0, title=self.title,
                                                           iconImage=logo,
                                                           thumbnailImage=logo,
                                                           url=url, mode=url_mode['mode'])

                                    if self._player.last_error:
                                        raise self._player.last_error
                                    defines.monitor.waitForAbort(1)
                                log.d(f'End playing url "{url}"')

                            elif not channel.is_availible():
                                if title_wo_hd not in self.proxytv:
                                    self.proxytv.search_by_name(title_wo_hd)
                                    log.d(self.proxytv)
                                    if self.proxytv[title]:
                                        for u_obj in self.proxytv[title]:
                                            for prov, u in u_obj.items():
                                                channel.insert(0, TChannel({'name': title, 'src': prov, 'player': 'tsp', 'url': u}))
                                    else:
                                        for u_obj in self.proxytv[title_wo_hd]:
                                            for prov, u in u_obj.items():
                                                channel.insert(0, TChannel({'name': title_wo_hd, 'src': prov, 'player': 'tsp', 'url': u}))

                                    for t, urls in self.proxytv.items():
                                        for u_obj in urls:
                                            for prov, u in u_obj.items():
                                                self.parent.channel_groups.addChannel(
                                                    TChannel({'name': t, 'src': prov, 'player': 'tsp', 'url': u}), src_name=prov, groupname=self.parent.cur_category)

                                if not channel.is_availible() and title_wo_hd in self.proxytv:
                                    if chli:
                                        chli.setLabel(f'[COLOR 0xFF333333]{chli.getLabel()}[/COLOR]')
                                    self.channelStop()

                            defines.monitor.waitForAbort(1)

                    except Exception as e:
                        log.d(e)
                        url_mode['availible'] = False
                        self.parent.showStatus(f'Ссылка недоступна для канала "{channel.title()}" в источнике {src_name}', timeout=5)
#
                    finally:
                        if players.Flags.channel_stop_requested() or defines.isCancel():
                            self.close()
                            return

    def run_selected_channel(self, timeout=0):

        def run():
            log.d(f'CHANNEL NUMBER IS: {self.channel_number}')
            if 0 < self.channel_number < self.parent.list.size() and self.parent.selitem_id != self.channel_number:
                self.parent.selitem_id = self.channel_number
                self.parent.Play()
#                 self.channelStop()
#                 self.close()
            else:
                self.hideStatus()
            self.channel_number = self.parent.selitem_id
            self.chinfo_label.setLabel(self.parent.list.getListItem(self.parent.selitem_id).getLabel())
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

    def showStatus(self, text, timeout=0):
        try:
            log.d(f"showStatus: {text}")
            if self.swinfo:
                self.swinfo.setLabel(text)
                self.swinfo.setVisible(True)
        except Exception as e:
            log.w(f"showStatus error: {e}")
        finally:
            self.timers.stop(MyPlayer.TIMER_HIDE_STATUS)
            if timeout:
                self.timers.start(MyPlayer.TIMER_HIDE_STATUS, threading.Timer(timeout, self.hideStatus))

    def hideStatus(self):
        try:
            if self.swinfo:
                self.swinfo.setVisible(False)
        except Exception as e:
            log.w(f"hideStatus error: {e}")

    def channelStop(self):
        if self._player:
            self._player.channelStop()
        else:
            players.Flags.channelStop()

    def switchSource(self):
        if self._player:
            self._player.switchSource()
        else:
            players.Flags.switchSource()

    def Stop(self):
        if self._player:
            return self._player.stop()

    def onAction(self, action):

        def viewEPG():
            selItem = self.parent.list.getListItem(self.channel_number)
            if selItem and selItem.getProperty("type") == 'channel':
                self.chinfo_label.setLabel(selItem.getLabel())
                self.showStatus('Переключение...')

                sel_ch = self.parent.get_channel_by_title(selItem.getProperty("title"))
                if sel_ch:
                    self.UpdateEpg(sel_ch)
                return True

#         log.d('Action {0} | ButtonCode {1}'.format(action.getId(), action.getButtonCode()))
        if action in MyPlayer.CANCEL_DIALOG or action.getId() == MyPlayer.ACTION_RBC:
            log.d(f'Close player {action.getId()} {action.getButtonCode()}')
            if self.timers.get(MyPlayer.TIMER_RUN_SEL_CHANNEL):
                self.channel_number = self.parent.selitem_id
                self.run_selected_channel()
                self.UpdateEpg(self.channel)
            else:
                self.close()

        elif action in (xbmcgui.ACTION_NEXT_ITEM, xbmcgui.ACTION_PREV_ITEM):
            self.switchSource()
        elif action in (xbmcgui.ACTION_STOP, xbmcgui.ACTION_PAUSE):
            self.channelStop()

        elif action in (
                xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_PAGE_UP, xbmcgui.ACTION_PAGE_DOWN):
            # IF ARROW UP AND DOWN PRESSED - SWITCH CHANNEL ##### @IgnorePep8
            if action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_PAGE_UP):
                self.dec_channel_number()
            else:
                self.inc_channel_number()

            if viewEPG():
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

                if viewEPG():
                    self.run_selected_channel(timeout=5)
        elif action.getId() == 0 and action.getButtonCode() == 61530:
            xbmc.executebuiltin('Action(FullScreen)')
            defines.monitor.waitForAbort(4)
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
            self.channelStop()
            self.close()
        elif controlID == MyPlayer.CONTROL_BUTTON_NEXT:
            self.Stop()

    def close(self):
        for name in self.timers:
            self.timers.stop(name)
        if self.visible.is_set():
            xbmcgui.WindowXML.close(self)
        self.visible.clear()

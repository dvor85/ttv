# -*- coding: utf-8 -*-
# Copyright (c) 20131 Torrent-TV.RU
# Writer (c) 2014, Welicobratov K.A., E-mail: 07pov23@gmail.com
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

# imports
import xbmc
import xbmcgui

import sys
import socket
import os
import threading
import random
import urllib
import copy
import defines
import logger
import utils
import json


log = logger.Logger('TSEngine')
fmt = utils.fmt


class TSengine(xbmc.Player):
    MODE_TORRENT = 'TORRENT'
    MODE_INFOHASH = 'INFOHASH'
    MODE_RAW = 'RAW'
    MODE_PID = 'PID'
    MODE_NONE = None

    _instance = None
    _lock = threading.Lock()

    @staticmethod
    def get_instance(parent=None, ipaddr='127.0.0.1', *args):
        if TSengine._instance is None:
            with TSengine._lock:
                if TSengine._instance is None:
                    TSengine._instance = TSengine(parent=parent, ipaddr=ipaddr, *args)
        return TSengine._instance

    def __init__(self, parent=None, ipaddr='127.0.0.1', *args):
        log("Init TSEngine")
        self.last_error = None
        self.quid = 0
        self.torrent = ''
        self.amalker = False
        self.parent = parent
        self.stream = False
        self.ace_engine = ''
        self.aceport = 0
        self.port_file = ''
        self.sock_thr = None
        self.link = None
        self.manual_stopped = True

        log.d(defines.ADDON.getSetting('ip_addr'))
        if defines.ADDON.getSetting('ip_addr'):
            self.server_ip = defines.ADDON.getSetting('ip_addr')
        else:
            self.server_ip = ipaddr
            defines.ADDON.setSetting('ip_addr', ipaddr)
        if defines.ADDON.getSetting('web_port'):
            self.webport = defines.ADDON.getSetting('webport')
        else:
            self.webport = '6878'

        if sys.platform.startswith('win'):
            self.ace_engine = self.getAceEngine_exe()
            log.d(fmt("AceEngine path: {0}", self.ace_engine))
            self.port_file = os.path.join(os.path.dirname(self.ace_engine), 'acestream.port')
            log.d(fmt("AceEngine port file: {0}", self.port_file))
            if os.path.exists(self.port_file):
                self.aceport = self.getWinPort()

        if self.aceport == 0:
            if defines.ADDON.getSetting('port'):
                self.aceport = utils.str2int(defines.ADDON.getSetting('port'))
            else:
                self.aceport = 62062

        if not defines.ADDON.getSetting('age'):
            defines.ADDON.setSetting('age', '1')
        if not defines.ADDON.getSetting('gender'):
            defines.ADDON.setSetting('gender', '1')
        log.d('Connect to AceEngine')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connectToTS()

    def onPlayBackStopped(self):
        log('onPlayBackStopped')
        if self.amalker:
            self.parent.amalkerWnd.close()
        else:
            self.stop()
            self.parent.player.close()

    def onPlayBackEnded(self):
        log('onPlayBackEnded')
        self.manual_stopped = False
        self.onPlayBackStopped()

    def onPlayBackStarted(self):
        try:
            log(fmt('onPlayBackStarted: {0} {1} {2}',
                    xbmcgui.getCurrentWindowId(), self.amalker, self.getPlayingFile()))
        except Exception as e:
            log.e(fmt('onPlayBackStarted: {0}', e))

        self.manual_stopped = True
        self.parent.hide_main_window()

    def sockConnect(self):
        self.sock.connect((self.server_ip, self.aceport))
        self.sock.setblocking(0)
        self.sock.settimeout(10)

    def checkConnect(self):
        for i in range(15):
            try:
                self.parent.showStatus(fmt("Подключение к AceEngine ({0})", i))
                self.sockConnect()
                return True
            except Exception as e:
                log.e(fmt("Подключение не удалось {0}", e))
                if not self.isCancel():
                    xbmc.sleep(995)
                else:
                    return

    def getAceEngine_exe(self):
        log.d('Считываем путь к ace_engine.exe')
        import _winreg
        t = None
        try:
            t = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, 'Software\\ACEStream')  # @UndefinedVariable
            return utils.true_enc(_winreg.QueryValueEx(t, 'EnginePath')[0])  # @UndefinedVariable

        except Exception as e:
            log.e('getAceEngine_exe error: %s' % e)
            return u''
        finally:
            if t:
                _winreg.CloseKey(t)  # @UndefinedVariable

    def getWinPort(self):
        log.d('Считываем порт')
        for i in range(15):
            if os.path.exists(self.port_file):
                with open(self.port_file, 'rb') as gf:
                    return utils.str2int(gf.read())
            else:
                self.parent.showStatus(fmt("Запуск AceEngine ({0})", i))
                if not self.isCancel():
                    xbmc.sleep(995)
                else:
                    break

        return 0

    def startEngine(self):
        import subprocess
        acestream_params = ["--live-cache-type", "memory"]
        if self.server_ip == '127.0.0.1':
            if sys.platform.startswith('win'):
                try:
                    log('try to start AceEngine for windows')

                    if self.port_file != '' and os.path.exists(self.port_file):
                        log.d(fmt('Remove {0}', self.port_file))
                        os.remove(self.port_file)

                    if not os.path.exists(self.port_file):
                        self.parent.showStatus("Запуск AceEngine")

                        p = subprocess.Popen([utils.fs_enc(self.ace_engine)] + acestream_params)
                        log.d(fmt('pid = {0}', p.pid))

                        self.aceport = self.getWinPort()
                        if self.aceport > 0:
                            defines.ADDON.setSetting('port', str(self.aceport))
                        else:
                            return

                except Exception as e:
                    log.e(fmt('Cannot start AceEngine {0}', e))
                    return
            else:
                log('try to start AceEngine for linux')
                acestream_params += ["--client-console"]
                try:
                    self.parent.showStatus("Запуск acestreamengine")
                    try:
                        p = subprocess.Popen(["acestreamengine"] + acestream_params)
                        log.d(fmt('pid = {0}', p.pid))
                    except Exception as e:
                        log.d(fmt('Error start acestreamengine for linux: {0}', e))
                        log('try to start AceEngine for Android')
                        xbmc.executebuiltin('XBMC.StartAndroidActivity("org.acestream.engine")')
                        xbmc.executebuiltin('XBMC.StartAndroidActivity("org.xbmc.kodi")')
                except Exception as e:
                    log.e(fmt('Cannot start AceEngine {0}', e))
                    return
        return True

    def get_key(self, key):
        #         try:
        #             r = defines.request(fmt("http://{url}/xbmc_get_key.php", url=defines.API_MIRROR, trys=1),
        #                                 params={'key': key})
        #             r.raise_for_status()
        #             return r.text
        #         except:
        import hashlib
        pkey = 'n51LvQoTlJzNGaFxseRK-uvnvX-sD4Vm5Axwmc4UcoD-jruxmKsuJaH0eVgE'
        sha1 = hashlib.sha1()
        sha1.update(key + pkey)
        key = sha1.hexdigest()
        pk = pkey.split('-')[0]
        return "%s-%s" % (pk, key)

    def connectToTS(self):
        log.d('Подключение к AceEngine %s %s ' %
              (self.server_ip, self.aceport))
        for t in range(3):
            try:
                log.d(fmt("Попытка подлючения ({0})", t))
                self.sockConnect()
                break
            except Exception as e:
                if self.startEngine():
                    if not self.checkConnect():
                        msg = fmt('Ошибка подключения к AceEngine: {0}', e)
                        log.f(msg)
                        self.parent.showStatus('Ошибка подключения к AceEngine!')
                    else:
                        break
                else:
                    msg = "Не удалось запустить AceEngine!"
                    self.parent.showStatus(msg)

                if not self.isCancel():
                    xbmc.sleep(995)
                else:
                    raise Exception('Cancel')
        else:
            msg = 'Ошибка подключения к AceEngine'
            self.parent.showStatus(msg)
            raise Exception(msg)

        log.d('Все ок')
        # Общаемся
        try:
            if self.sendCommand('HELLOBG version=4'):
                self.Wait(TSMessage.HELLOTS)
                msg = self.sock_thr.getTSMessage()
                if msg.getType() == TSMessage.HELLOTS:
                    if not msg.getParams().get('key'):
                        raise IOError('Incorrect msg from AceEngine')
                    ace_version = msg.getParams().get('version')
                    if ace_version < '3':
                        raise ValueError("It's necessary to update AceStream")

                self.sock_thr.msg = TSMessage()
                if self.sendCommand('READY key=' + self.get_key(msg.getParams().get('key'))):
                    self.Wait(TSMessage.AUTH)
                    msg = self.sock_thr.getTSMessage()
                    if msg.getType() == TSMessage.AUTH:
                        if utils.str2int(msg.getParams()) == 0:
                            log.w('Пользователь не зарегистрирован')
                    else:
                        raise IOError('Incorrect msg from AceEngine')

        except IOError as io:
            log.e(fmt('Error while auth: {0}', io))
            self.last_error = str(io)
            self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
            return
        except ValueError as ve:
            log.e(fmt('AceStream version error: {0}', ve))
            self.last_error = str(ve)
            self.parent.showStatus("Необходимо обновить AceStream до версии 3")
            return
        except Exception as e:
            log.e(fmt('connectToTS error: {0}', e))

        log.d('End Init AceEngine')
        self.parent.hideStatus()

    def sendCommand(self, cmd):
        for t in range(3):  # @UnusedVariable
            try:
                if not (self.sock_thr and self.sock_thr.is_active()):
                    if cmd not in ("STOP", "SHUTDOWN"):
                        self.createThread()
                    else:
                        return

                log.d(fmt('>> "{0}"', cmd))
#                 raise Exception('Test Exception')
                self.sock.send(cmd + '\r\n')
                return True
            except Exception as e:
                log.e(fmt('ERROR: "{0}" while Send command: "{1}"', e, cmd))

        if self.sock_thr and self.sock_thr.is_active():
            self.sock_thr.end()

    def isCancel(self):
        return defines.isCancel()

    def Wait(self, msg):
        log.d(fmt('wait message: {0}', msg))
        a = 0
        try:
            while self.sock_thr.getTSMessage().getType() != msg and not self.sock_thr.error and not self.isCancel():
                xbmc.sleep(122)
                if not self.stream:
                    xbmc.sleep(122)
                a += 1
                if a >= 120:
                    log.w('AceEngine is freeze')
                    self.parent.showStatus("Ошибка ожидания. Операция прервана")
                    raise ValueError('AceEngine is freeze')
        except:
            self.stop()

    def createThread(self):
        self.sock_thr = SockThread(self.sock)
        self.sock_thr.state_method = self.showState
        self.sock_thr.owner = self
        self.sock_thr.start()

    def load_torrent(self, torrent, mode):
        log(fmt("Load Torrent: {0}, mode: {1}", torrent, mode))
        cmdparam = ''
        self.mode = mode
        if mode != TSengine.MODE_PID:
            cmdparam = ' 0 0 0'
        self.quid = str(random.randint(0, 0x7fffffff))
        self.torrent = torrent
        comm = 'LOADASYNC ' + self.quid + ' ' + mode + ' ' + torrent + cmdparam
        self.parent.showStatus("Загрузка торрента")
        self.stop()

        if self.sendCommand(comm):
            self.Wait(TSMessage.LOADRESP)
            msg = self.sock_thr.getTSMessage()
            log.d('load_torrent - %s' % msg.getType())
            if msg.getType() == TSMessage.LOADRESP:
                try:
                    log.d('Compile file list')
                    jsonfile = msg.getParams()['json']
                    if 'files' not in jsonfile:
                        self.parent.showStatus(jsonfile['message'])
                        self.last_error = Exception(jsonfile['message'])
                        log.e('Compile file list %s' % self.last_error)
                        return
                    self.count = len(jsonfile['files'])
                    self.files = {}
                    for f in jsonfile['files']:
                        self.files[f[1]] = urllib.unquote_plus(urllib.quote(f[0]))
                    log.d('End Compile file list')
                except Exception as e:
                    log.e(fmt('load_torrent error: {0}', e))
                    self.last_error = e
                    self.end()
            else:
                self.last_error = 'Incorrect msg from AceEngine'
                self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
                log.f('Incorrect msg from AceEngine %s' % msg.getType())
                self.stop()
                return

            self.parent.hideStatus()

    def showState(self, state):
        try:
            if state.getType() == TSMessage.STATUS and self.parent:
                _params = state.getParams()
                if _params.get('main'):

                    _descr = _params['main'].split(';')
                    if _descr[0] == 'prebuf':
                        log.d('showState: Пытаюсь показать состояние')
                        self.parent.showStatus('Пребуферизация %s' % _descr[1])
                    elif _descr[0] == 'check':
                        log.d('showState: Проверка %s' % _descr[1])
                        self.parent.showStatus('Проверка %s' % _descr[1])
#                     elif _descr[0] == 'dl':
#                         self.parent.showInfoStatus('Total:%s DL:%s UL:%s' % (_descr[1], _descr[3], _descr[5]))
#                     elif _descr[0] == 'buf':
#                         self.parent.showInfoStatus('Buf:%s DL:%s UL:%s' % (_descr[1], _descr[5], _descr[7]))
#                     else:
#                         self.parent.showInfoStatus('%s' % _params)

            elif state.getType() == TSMessage.EVENT:
                if state.getParams() == 'getuserdata':
                    self.sendCommand('USERDATA [{"gender": %s}, {"age": %s}]' % (utils.str2int(defines.GENDER) + 1,
                                                                                 utils.str2int(defines.AGE) + 1))
                elif state.getParams().startswith('showdialog'):
                    _parts = state.getParams().split()
                    self.parent.showStatus(fmt('{0}: {1}', urllib.unquote(_parts[2].split('=')[1]),
                                               urllib.unquote(_parts[1].split('=')[1])))
            elif state.getType() == TSMessage.ERROR:
                self.parent.showStatus(state.getParams())

        except Exception as e:
            log.e(fmt('showState error: "{0}"', e))

    def play_url_ind(self, index=0, title='', icon=None, thumb=None, torrent=None, mode=None):
        if self.last_error:
            return
        if torrent:
            self.torrent = torrent
            self.mode = mode
        else:
            self.parent.showStatus('Нечего проигрывать')
            return
        spons = '0 0 0' if self.mode != TSengine.MODE_PID else ''
        comm = fmt('START {mode} {torrent} {index} {spons}', **{'mode': self.mode,
                                                                'torrent': self.torrent,
                                                                'index': index,
                                                                'spons': spons})
        log.d("Запуск торрента")
        self.stop()
        xbmc.sleep(4)
        if self.sendCommand(comm):
            self.parent.showStatus("Запуск торрента")
            self.Wait(TSMessage.START)
            msg = self.sock_thr.getTSMessage()
            if msg.getType() == TSMessage.START:
                try:
                    _params = msg.getParams()
                    if not _params.get('url'):
                        self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
                        raise Exception('Incorrect msg from AceEngine %s' % msg.getType())

                    self.amalker = 'ad' in _params and 'interruptable' not in _params
                    self.link = _params['url'].replace('127.0.0.1', self.server_ip).replace('6878', self.webport)
                    log.d('Преобразование ссылки: %s' % self.link)
                    self.title = title
                    self.icon = icon

                    self.sock_thr.msg = TSMessage()
                    if self.amalker:
                        self.parent.showStatus('Рекламный ролик')
                    log.d('Первый запуск. Окно = %s. Реклама = %s' % (xbmcgui.getCurrentWindowId(), self.amalker))
                    self.icon = icon
                    self.thumb = thumb
                    lit = xbmcgui.ListItem(title, iconImage=icon, thumbnailImage=thumb)
                    self.play(self.link, lit, windowed=True)
                    self.parent.player.Show()
                    self.loop()
                except Exception as e:
                    log.e(fmt('play_url_ind error: {0}', e))
                    self.last_error = e
                    self.parent.showStatus("Ошибка. Операция прервана")
            else:
                self.last_error = 'Incorrect msg from AceEngine %s' % msg.getType()
                log.e(self.last_error)
                self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
            self.stop()

    def loop(self):
        while self.isPlaying() and not self.isCancel():
            if self.isPlaying() and self.amalker and (self.getTotalTime() - self.getTime()) < 0.5:
                self.parent.amalkerWnd.close()
                break
            try:
                if not self.isCancel():
                    xbmc.sleep(250)
                else:
                    log.d("XBMC Shutdown")
                    return

            except Exception as e:
                log.e(fmt('ERROR SLEEPING: {0}', e))
                self.end()
                raise

        if self.amalker and self.sendCommand('PLAYBACK ' + self.play_url + ' 100'):
            self.Wait(TSMessage.START)
            msg = self.sock_thr.getTSMessage()
            if msg.getType() == TSMessage.START:
                try:
                    _params = msg.getParams()
                    if not _params.get('url'):
                        raise Exception('Incorrect msg from AceEngine %s' % msg.getType())
                    if _params.get('stream') and _params['stream'] == '1':
                        self.stream = True
                    else:
                        self.stream = False

                    self.play_url = _params['url'].replace('127.0.0.1', self.server_ip).replace('6878', self.webport)
                    self.amalker = 'ad' in _params and 'interruptable' not in _params
                    if self.amalker:
                        self.parent.showStatus('Рекламный ролик')

                    lit = xbmcgui.ListItem(self.title, iconImage=self.icon, thumbnailImage=self.thumb)
                    self.play(self.play_url, lit, windowed=True)
                    self.loop()
                except Exception as e:
                    log.e(fmt('play_url_ind loop error: {0}', e))
                    self.last_error = e
                    self.parent.showStatus("Ошибка. Операция прервана")
            else:
                self.last_error = 'Incorrect msg from AceEngine %s' % msg.getType()
                self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
                log.e(self.last_error)
        self.stop()

    def end(self):
        self.link = None
        if self.sendCommand('STOP'):
            self.sendCommand('SHUTDOWN')
        self.last_error = None
        if self.sock_thr:
            self.sock_thr.end()
            self.sock_thr = None
        self.sock.close()
        xbmc.Player.stop(self)

    def stop(self):
        log('stop player method')
        self.link = None
        self.sendCommand('STOP')
        if self.sock_thr:
            self.sock_thr.end()
            self.sock_thr.join()
            self.sock_thr = None
        self.last_error = None
        xbmc.Player.stop(self)


class TSMessage:
    ERROR = 'ERROR'
    HELLOTS = 'HELLOTS'
    AUTH = 'AUTH'
    LOADRESP = 'LOADRESP'
    STATUS = 'STATUS'
    STATE = 'STATE'
    START = 'START'
    EVENT = 'EVENT'
    PAUSE = 'PAUSE'
    RESUME = 'RESUME'
    NONE = ''

    def __init__(self):
        self.type = TSMessage.NONE
        self.params = {}

    def getType(self):
        return self.type

    def getParams(self):
        return self.params

    def setParams(self, value):
        self.params = value

    def setType(self, value):
        self.type = value


class SockThread(threading.Thread):

    def __init__(self, _sock):
        log.d('Init SockThread')
        threading.Thread.__init__(self)
        self.name = 'SockThread'
        self.daemon = False
        self.sock = _sock
        self.buffer = 65020
        self.isRecv = False
        self.lastRecv = ''
        self.lstCmd = ''
        self.active = False
        self.error = None
        self.msg = TSMessage()
        self.state_method = None
        self.owner = None

    def run(self):
        self.active = True

        def isCancel():
            return not self.is_active() or self.error or self.owner.isCancel()

        log.d('Start SockThread')
        while not isCancel():
            try:
                xbmc.sleep(32)
                self.lastRecv += self.sock.recv(self.buffer)
                if self.lastRecv.find('\r\n') > -1:
                    cmds = self.lastRecv.split('\r\n')
                    for cmd in cmds:
                        if len(cmd.replace(' ', '')) > 0 and not isCancel():
                            log.d(fmt('<< "{0}"', cmd))
                            self._constructMsg(cmd)
                    self.lastRecv = ''
            except Exception as e:
                self.isRecv = True
                self.end()
                self.error = e
                log.e('RECV THREADING %s' % e)
                _msg = TSMessage()
                _msg.type = TSMessage.ERROR
                _msg.params = 'Ошибка соединения с AceEngine'
                self.state_method(_msg)
        log.d('Exit from sock thread')
        self.error = None

    def _constructMsg(self, strmsg):
        posparam = strmsg.find(' ')
        if posparam == -1:
            _msg = strmsg
        else:
            _msg = strmsg[:posparam]

        if _msg == TSMessage.HELLOTS:
            self.msg = TSMessage()
            self.msg.setType(TSMessage.HELLOTS)
            log.d(strmsg)
            prms = strmsg[posparam + 1:].split(" ")
            self.msg.setParams({})
            for prm in prms:
                _prm = prm.split('=')
                self.msg.getParams()[_prm[0]] = _prm[1]
        elif _msg == TSMessage.AUTH:
            self.msg = TSMessage()
            self.msg.setType(TSMessage.AUTH)
            self.msg.setParams(strmsg[posparam + 1:])
        elif _msg == TSMessage.LOADRESP:
            self.msg = TSMessage()
            strparams = strmsg[posparam + 1:]
            posparam = strparams.find(' ')
            _params = {}
            _params['qid'] = strparams[:posparam]
            _params['json'] = json.loads(strparams[posparam + 1:])
            self.msg.setType(TSMessage.LOADRESP)
            self.msg.setParams(_params)
        elif _msg == TSMessage.STATUS:
            buf = strmsg[posparam + 1:].split('|')
            _params = {}
            for item in buf:
                buf1 = item.split(':')
                _params[buf1[0]] = buf1[1]

            if strmsg.find('err') >= 0:
                raise Exception(strmsg[posparam + 1:])
            elif self.state_method:
                self.status = TSMessage()
                self.status.setType(TSMessage.STATUS)
                self.status.setParams(_params)
                self.state_method(self.status)
            else:
                log.w('I DONT KNOW HOW IT PROCESS %s' % strmsg)
        elif _msg == TSMessage.STATE:
            if self.state_method:
                self.state = TSMessage()
                self.state.setType(TSMessage.STATE)
                self.state.setParams(strmsg[posparam + 1:])
                self.state_method(self.state)
        elif _msg == TSMessage.EVENT:
            self.event = TSMessage()
            _strparams = strmsg[posparam + 1:]
            self.event.setType(TSMessage.EVENT)
            self.event.setParams(_strparams)
            self.state_method(self.event)
        elif _msg == TSMessage.START:
            self.msg = TSMessage()
            _strparams = strmsg[posparam + 1:].split(' ')
            _params = {}
            log.d(strmsg)
            if _strparams.__len__() >= 2:
                log.d('%s' % _strparams)
                _params['url'] = _strparams[0].split("=")[1].replace("%3A", ":")
                prms = _strparams[1:]
                for prm in prms:
                    sprm = prm.split('=')
                    _params[sprm[0]] = sprm[1]

            else:
                _params['url'] = _strparams[0].split("=")[1].replace("%3A", ":")
            self.msg.setType(TSMessage.START)
            self.msg.setParams(_params)
        elif _msg in (TSMessage.PAUSE, TSMessage.RESUME):
            msg = TSMessage()
            msg.setType(_msg)
            self.state_method(msg)

    def getTSMessage(self):
        return copy.deepcopy(self.msg)

    def is_active(self):
        return self.active

    def end(self):
        self.active = False

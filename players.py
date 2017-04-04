# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

# imports
import xbmc
import xbmcgui

import socket
import os
import threading
import subprocess
import random
import urllib
import defines
import logger
import utils
import json
import time


log = logger.Logger(__name__)
fmt = utils.fmt
sys_platform = defines.platform()['os']
manual_stopped = threading.Event()
switch_source = threading.Event()


class TPlayer(xbmc.Player):

    _instance = None
    _lock = threading.RLock()

    @staticmethod
    def get_instance(parent=None, *args):
        try:
            if TPlayer._instance is None:
                with TPlayer._lock:
                    if TPlayer._instance is None:
                        TPlayer._instance = TPlayer(parent=parent, *args)
        except Exception as e:
            log.e(fmt('get_instance error: {0}', e))
            TPlayer._instance = None
        finally:
            return TPlayer._instance

    def __init__(self, parent=None, *args):
        self.parent = parent

        self.link = None  # Для передачи ссылки плееру

    def onPlayBackStopped(self):
        log('onPlayBackStopped')
        self.stop()

    def onPlayBackEnded(self):
        log('onPlayBackEnded')
        self.next_source()

    def onPlayBackStarted(self):
        try:
            log(fmt('onPlayBackStarted: {0} {1}', xbmcgui.getCurrentWindowId(),  self.getPlayingFile()))
        except Exception as e:
            log.e(fmt('onPlayBackStarted error: {0}', e))

        manual_stopped.set()
        switch_source.clear()
        self.parent.hide_main_window()

    def loop(self):
        while self.isPlaying() and not defines.isCancel():
            try:
                xbmc.sleep(250)
            except Exception as e:
                log.e(fmt('ERROR SLEEPING: {0}', e))
                self.end()
                raise

        self.stop()

    def play_item(self, title='', icon='', thumb='', *args, **kwargs):
        li = xbmcgui.ListItem(title, iconImage=icon, thumbnailImage=thumb)
        if not self.link:
            self.parent.showStatus('Нечего проигрывать')
            return
        self.play(self.link, li, windowed=True)
        self.parent.player.Show()
        self.parent.player.hideStatus()
        self.loop()
        return not switch_source.is_set() or manual_stopped.is_set()

    def next_source(self):
        switch_source.set()
        manual_stopped.clear()
        self.stop()

    def end(self):
        xbmc.Player.stop(self)

    def stop(self):
        xbmc.Player.stop(self)


class AcePlayer(TPlayer):
    MODE_TORRENT = 'TORRENT'
    MODE_INFOHASH = 'INFOHASH'
    MODE_RAW = 'RAW'
    MODE_PID = 'PID'
    MODE_NONE = None

    TIMEOUT_FREEZE = utils.str2num(defines.ADDON.getSetting('freeze_timeout'), 20)

    _instance = None
    _lock = threading.RLock()

    @staticmethod
    def get_instance(parent=None, ipaddr='127.0.0.1', *args):
        try:
            if AcePlayer._instance is None:
                with AcePlayer._lock:
                    if AcePlayer._instance is None:
                        AcePlayer._instance = AcePlayer(parent=parent, ipaddr=ipaddr, *args)
        except Exception as e:
            log.e(fmt('get_instance error: {0}', e))
            AcePlayer._instance = False
        finally:
            return AcePlayer._instance

    def __init__(self, parent=None, ipaddr='127.0.0.1', *args):
        TPlayer.__init__(self, parent=parent, *args)
        log("Init AceEngine")
        if defines.ADDON.getSetting('use_ace') == "false":
            raise Exception("Acestream player is disabled")
        self.last_error = None
        self.quid = 0
        self.ace_engine = ''
        self.aceport = utils.str2int(defines.ADDON.getSetting('port'), 62062)
        self.port_file = ''
        self.sock_thr = None
        self.prebuf = {"last_update": time.time(), "value": 0}
        self.waiting = {"msg": None, "event": threading.Event()}

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

        self.ace_engine = self._getAceEngine_path()
        log.d(fmt('AceEngine path: "{0}"', self.ace_engine))

        if sys_platform == "windows":
            self.port_file = os.path.join(os.path.dirname(self.ace_engine), 'acestream.port')
            log.d(fmt('AceEngine port file: "{0}"', self.port_file))

        if not defines.ADDON.getSetting('age'):
            defines.ADDON.setSetting('age', '1')
        if not defines.ADDON.getSetting('gender'):
            defines.ADDON.setSetting('gender', '1')
        log.d('Connect to AceEngine')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._connectToTS()

    def _sockConnect(self):
        self.sock.connect((self.server_ip, self.aceport))
        self.sock.setblocking(0)
        self.sock.settimeout(10)

    def _checkConnect(self):
        for i in range(15):
            try:
                self.parent.showStatus(fmt("Подключение к AceEngine ({0})", i))
                self._sockConnect()
                return True
            except Exception as e:
                log.e(fmt("Подключение не удалось {0}", e))
                if not defines.isCancel():
                    xbmc.sleep(995)
                else:
                    return

    def _getAceEngine_path(self):
        log.d('Считываем путь к ace_engine.exe')
        if sys_platform == 'windows':
            import _winreg
            t = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, 'Software\\ACEStream')  # @UndefinedVariable
            try:
                return utils.true_enc(_winreg.QueryValueEx(t, 'EnginePath')[0])  # @UndefinedVariable
            finally:
                _winreg.CloseKey(t)  # @UndefinedVariable
        elif sys_platform == 'linux':
            return utils.true_enc(subprocess.check_output(["which", "acestreamengine"]).strip())
        else:
            return ""

    def _getWinPort(self):
        log.d('Считываем порт')
        for i in range(15):
            if os.path.exists(self.port_file):
                with open(self.port_file, 'rb') as gf:
                    return utils.str2int(gf.read())
            else:
                self.parent.showStatus(fmt("Запуск AceEngine ({0})", i))
                if not defines.isCancel():
                    xbmc.sleep(995)
                else:
                    break

        return 0

    def _killEngine(self):
        if sys_platform == "windows":
            try:
                log.d(fmt('Kill "{0}"', os.path.basename(self.ace_engine)))
                si = subprocess.STARTUPINFO()
                si.dwFlags = subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE

                subprocess.call(["taskkill", "/F", "/IM", os.path.basename(self.ace_engine)], shell=False, startupinfo=si)
                log.d(fmt('Remove "{0}"', self.port_file))
                os.remove(self.port_file)
            except Exception as e:
                log.d(fmt("_killEngine error: {0}", e))

    def _startEngine(self):
        acestream_params = ["--live-cache-type", "memory"]
        if self.server_ip == '127.0.0.1':
            if sys_platform == 'windows':
                try:
                    self._killEngine()

                    log('try to start AceEngine for windows')
                    self.parent.showStatus("Запуск AceEngine")
                    p = subprocess.Popen([utils.fs_enc(self.ace_engine)] + acestream_params)
                    log.d(fmt('pid = {0}', p.pid))

                    self.aceport = self._getWinPort()
                    if self.aceport > 0:
                        defines.ADDON.setSetting('port', str(self.aceport))
                    else:
                        return

                except Exception as e:
                    log.e(fmt('Cannot start AceEngine {0}', e))
                    return
            elif sys_platform == 'linux':
                log('try to start AceEngine for linux')
                acestream_params += ["--client-console"]
                try:
                    self.parent.showStatus("Запуск acestreamengine")
                    p = subprocess.Popen([self.ace_engine] + acestream_params)
                    log.d(fmt('pid = {0}', p.pid))
                except Exception as e:
                    log.e(fmt('Cannot start AceEngine {0}', e))
                    return
            elif sys_platform == 'android':
                log('try to start AceEngine for Android')
                xbmc.executebuiltin('XBMC.StartAndroidActivity("org.acestream.engine")')
                xbmc.executebuiltin('XBMC.StartAndroidActivity("org.xbmc.kodi")')
            else:
                return False
        return True

    def _get_key(self, key):
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
        return fmt("{pk}-{key}", pk=pk, key=key)

    def _connectToTS(self):
        log.d(fmt('Подключение к AceEngine {0} {1}', self.server_ip, self.aceport))
        for t in range(3):
            try:
                log.d(fmt("Попытка подлючения ({0})", t))
                self._sockConnect()
                break
            except Exception as e:
                if self._startEngine():
                    if not self._checkConnect():
                        msg = fmt('Ошибка подключения к AceEngine: {0}', e)
                        log.f(msg)
                        self.parent.showStatus('Ошибка подключения к AceEngine!')
                    else:
                        break
                else:
                    msg = "Не удалось запустить AceEngine!"
                    self.parent.showStatus(msg)

                if not defines.isCancel():
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
            if self._send_command('HELLOBG version=4'):
                msg = self._wait_message(TSMessage.HELLOTS)
                if msg:
                    if not msg.getParams().get('key'):
                        raise IOError('Incorrect msg from AceEngine')
                    ace_version = msg.getParams().get('version')
                    if ace_version < '3':
                        raise ValueError("It's necessary to update AceStream")

                    if self._send_command('READY key=' + self._get_key(msg.getParams().get('key'))):
                        msg = self._wait_message(TSMessage.AUTH)
                        if msg:
                            if utils.str2int(msg.getParams()) == 0:
                                log.w('Пользователь не зарегистрирован')
                        else:
                            raise IOError('Incorrect msg from AceEngine')

        except IOError as io:
            log.e(fmt('Error while auth: {0}', io))
            self.last_error = io
            self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
            return
        except ValueError as ve:
            log.e(fmt('AceStream version error: {0}', ve))
            self.last_error = ve
            self.parent.showStatus("Необходимо обновить AceStream до версии 3")
            return
        except Exception as e:
            log.e(fmt('_connectToTS error: {0}', e))

        log.d('End Init AceEngine')
        self.parent.hideStatus()

    def _send_command(self, cmd):
        for t in range(3):  # @UnusedVariable
            try:
                if not (self.sock_thr and self.sock_thr.is_active()):
                    if cmd not in ("STOP", "SHUTDOWN"):
                        self._createThread()
                    else:
                        return

                log.d(fmt('>> "{0}"', cmd))
#                 raise Exception('Test Exception')
                self.sock.send(cmd + '\r\n')
                return True
            except Exception as e:
                log.e(fmt('_send_command error: "{0}" cmd: "{1}"', e, cmd))

        if self.sock_thr and self.sock_thr.is_active():
            self.sock_thr.end()

    def _wait_message(self, msg):
        """
        Wait message
        :msg: Message for wait (START, AUTH, etc)
        :return: TSMessage object if wait was successfuly, else None
        """
        log.d(fmt('wait message: {0}', msg))
        try:
            self.waiting['msg'] = msg
            self.waiting['event'].clear()
            for t in xrange(AcePlayer.TIMEOUT_FREEZE * 3):  # @UnusedVariable
                if not self.waiting['msg'] or self.sock_thr.error or defines.isCancel():
                    raise ValueError(fmt('Abort waiting message: "{0}"', msg))
                if self.waiting['event'].wait(1):
                    return self.waiting['msg']

            self.parent.showStatus("Ошибка ожидания. Операция прервана")
            raise ValueError('AceEngine is freeze')

        except Exception as e:
            log.e(fmt('_wait_message error: {0}', e))
            self.waiting["msg"] = None
            self.next_source()

    def _createThread(self):
        self.sock_thr = SockThread(self.sock)
        self.sock_thr.state_handler = self._stateHandler
        self.sock_thr.owner = self
        self.sock_thr.start()

    def _load_torrent(self, torrent, mode):
        log(fmt("Load Torrent: {0}, mode: {1}", torrent, mode))
        cmdparam = ''
        if mode != AcePlayer.MODE_PID:
            cmdparam = ' 0 0 0'
        self.quid = str(random.randint(0, 0x7fffffff))
        comm = 'LOADASYNC ' + self.quid + ' ' + mode + ' ' + torrent + cmdparam
        self.parent.showStatus("Загрузка торрента")
        self.stop()

        if self._send_command(comm):
            msg = self._wait_message(TSMessage.LOADRESP)
            if msg:
                try:
                    log.d(fmt('_load_torrent - {0}', msg.getType()))
                    log.d('Compile file list')
                    jsonfile = msg.getParams()['json']
                    if 'files' not in jsonfile:
                        self.parent.showStatus(jsonfile['message'])
                        self.last_error = Exception(jsonfile['message'])
                        log.e(fmt('Compile file list {0}', self.last_error))
                        return
                    self.count = len(jsonfile['files'])
                    self.files = {}
                    for f in jsonfile['files']:
                        self.files[f[1]] = urllib.unquote_plus(urllib.quote(f[0]))
                    log.d('End Compile file list')
                except Exception as e:
                    log.e(fmt('_load_torrent error: {0}', e))
                    self.last_error = e
                    self.end()
            else:
                self.last_error = 'Incorrect msg from AceEngine'
                self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
                self.stop()
                return

            self.parent.hideStatus()

    def _stateHandler(self, state):
        """
        Run when a TSMessage are received.
        If a message is waiting, then stop waiting.
        :state: Received TSMessage
        """
        try:
            if state.getType() == TSMessage.STATUS and self.parent:
                _params = state.getParams()
                if _params.get('main'):
                    _descr = _params['main'].split(';')

                    if _descr[0] == 'starting':
                        self.prebuf['value'] = 0

                    elif _descr[0] == 'prebuf':
                        if _descr[1] != self.prebuf['value']:
                            self.prebuf['last_update'] = state.getTime()
                            self.prebuf['value'] = _descr[1]
                            log.d('_stateHandler: Пытаюсь показать состояние')
                            self.parent.showStatus(fmt('Пребуферизация {0}', self.prebuf['value']))
                            self.parent.player.showStatus(fmt('Пребуферизация {0}', self.prebuf['value']))

                        if time.time() - self.prebuf['last_update'] >= AcePlayer.TIMEOUT_FREEZE:
                            log.w('AceEngine is freeze')
                            self.next_source()

                    elif _descr[0] == 'check':
                        log.d(fmt('_stateHandler: Проверка {0}', _descr[1]))
                        self.parent.showStatus(fmt('Проверка {0}', _descr[1]))
#                     elif _descr[0] == 'dl':
#                         self.parent.showInfoStatus('Total:%s DL:%s UL:%s' % (_descr[1], _descr[3], _descr[5]))
                    elif _descr[0] == 'buf':
                        # self.parent.showStatus('Буферизация: %s DL: %s UL: %s' % (_descr[1],
                        # _descr[5], _descr[7])) @IgnorePep8

                        if _descr[1] != self.prebuf['value']:
                            self.prebuf['last_update'] = state.getTime()
                            self.prebuf['value'] = _descr[1]
#                             self.parent.player.showStatus(fmt('Буферизация {0}', self.prebuf['value']))
                        if time.time() - self.prebuf['last_update'] >= AcePlayer.TIMEOUT_FREEZE:
                            self.parent.player.showStatus(fmt('Пребуферизация {0}', self.prebuf['value']))
                            log.w('AceEngine is freeze')
                            self.next_source()

#                         self.parent.showInfoStatus('Buf:%s DL:%s UL:%s' % (_descr[1], _descr[5], _descr[7]))
#                     else:
#                         self.parent.showInfoStatus('%s' % _params)
            elif state.getType() in (TSMessage.RESUME, TSMessage.PAUSE, TSMessage.START):
                self.prebuf['value'] = 0

            elif state.getType() == TSMessage.EVENT:
                if state.getParams() == 'getuserdata':
                    self._send_command(fmt('USERDATA [{"gender": {0}}, {"age": {1}}]',
                                           utils.str2int(defines.GENDER) + 1,
                                           utils.str2int(defines.AGE) + 1))
                elif state.getParams().startswith('showdialog'):
                    _parts = state.getParams().split()
                    self.parent.showStatus(fmt('{0}: {1}', urllib.unquote(_parts[2].split('=')[1]),
                                               urllib.unquote(_parts[1].split('=')[1])))
            elif state.getType() == TSMessage.ERROR:
                self.parent.showStatus(state.getParams())

        except Exception as e:
            log.e(fmt('_stateHandler error: "{0}"', e))
        finally:
            try:
                if self.waiting['msg'] == state.getType():
                    self.waiting['msg'] = state
                    self.waiting['event'].set()

            except Exception as e:
                log.e(fmt('_stateHandler error: "{0}"', e))

    def play_item(self, title='', icon='', thumb='', *args, **kwargs):
        res = None
        if self.last_error:
            return
        url = kwargs.get('url')
        mode = kwargs.get('mode')
        index = kwargs.get('index')
        if not url:
            self.parent.showStatus('Нечего проигрывать')
            return
        spons = '0 0 0' if mode != AcePlayer.MODE_PID else ''
        comm = fmt('START {mode} {torrent} {index} {spons}',
                   mode=mode,
                   torrent=url,
                   index=index,
                   spons=spons)
        log.d("Запуск торрента")
        xbmc.sleep(4)
        if self._send_command(comm):
            self.parent.showStatus("Запуск торрента")
            msg = self._wait_message(TSMessage.START)
            if msg:
                try:
                    _params = msg.getParams()
                    if not _params.get('url'):
                        self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
                        raise Exception(fmt('Incorrect msg from AceEngine {0}', msg.getType()))

                    self.link = _params['url'].replace('127.0.0.1', self.server_ip).replace('6878', self.webport)
                    log.d(fmt('Преобразование ссылки: {0}', self.link))
                    res = TPlayer.play_item(self, title, icon, thumb)
                except Exception as e:
                    log.e(fmt('play_item error: {0}', e))
                    self.last_error = e
                    self.parent.showStatus("Ошибка. Операция прервана")
            else:
                self.last_error = 'Incorrect msg from AceEngine'
                log.e(self.last_error)
                self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
            self.stop()
            return res

    def end(self):
        self.link = None
        if self._send_command('STOP'):
            self._send_command('SHUTDOWN')
        self.waiting['msg'] = None
        self.last_error = None
        if self.sock_thr:
            self.sock_thr.end()
            self.sock_thr = None
        self.sock.close()
        TPlayer.end(self)

    def stop(self):
        log('stop player method')
        self.link = None
        self._send_command('STOP')
        self.waiting['msg'] = None
        if self.sock_thr:
            self.sock_thr.end()
            self.sock_thr.join()
            self.sock_thr = None
        self.last_error = None
        TPlayer.stop(self)


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

    def __init__(self, tstype='', params=''):
        self.type = tstype
        self.update_time = time.time()
        self.params = params

    def getTime(self):
        return self.update_time

    def getType(self):
        return self.type

    def getParams(self):
        return self.params


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
        self.active = False
        self.error = None
        self.state_handler = None
        self.owner = None

    def run(self):
        self.active = True

        def isCancel():
            return not self.is_active() or self.error or defines.isCancel()

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
                log.e(fmt('RECV THREADING {0}', e))
                _msg = TSMessage(TSMessage.ERROR)
                _msg.params = 'Ошибка соединения с AceEngine'
                self.state_handler(_msg)
        log.d('Exit from sock thread')
        self.error = None

    def _constructMsg(self, strmsg):
        posparam = strmsg.find(' ')
        if posparam == -1:
            _msg = strmsg
        else:
            _msg = strmsg[:posparam]

        _params = {}

        if _msg == TSMessage.HELLOTS:
            log.d(strmsg)
            prms = strmsg[posparam + 1:].split(" ")
            for prm in prms:
                _prm = prm.split('=')
                _params[_prm[0]] = _prm[1]

        elif _msg == TSMessage.LOADRESP:
            strparams = strmsg[posparam + 1:]
            posparam = strparams.find(' ')
            _params['qid'] = strparams[:posparam]
            _params['json'] = json.loads(strparams[posparam + 1:])

        elif _msg == TSMessage.STATUS:
            buf = strmsg[posparam + 1:].split('|')
            for item in buf:
                buf1 = item.split(':')
                _params[buf1[0]] = buf1[1]

            if strmsg.find('err') >= 0:
                raise Exception(strmsg[posparam + 1:])

        elif _msg == TSMessage.START:
            _strparams = strmsg[posparam + 1:].split(' ')
            log.d(strmsg)
            if _strparams.__len__() >= 2:
                log.d(_strparams)
                _params['url'] = _strparams[0].split("=")[1].replace("%3A", ":")
                prms = _strparams[1:]
                for prm in prms:
                    sprm = prm.split('=')
                    _params[sprm[0]] = sprm[1]

            else:
                _params['url'] = _strparams[0].split("=")[1].replace("%3A", ":")

        else:
            _params = strmsg[posparam + 1:]

        self.state_handler(TSMessage(_msg, _params))

    def is_active(self):
        return self.active

    def end(self):
        self.active = False


class NoxPlayer(TPlayer):

    _instance = None
    _lock = threading.RLock()

    def __init__(self, parent=None, *args):
        TPlayer.__init__(self, parent=parent, *args)
        log('Init noxbit player')
        if defines.ADDON.getSetting('use_nox') == "false":
            raise Exception("Noxbit player is disabled")
        self.ip = defines.ADDON.getSetting('nox_ip')
        self.port = utils.str2int(defines.ADDON.getSetting('nox_port'))
        self._checkNox()

    @staticmethod
    def get_instance(parent=None, *args):
        try:
            if NoxPlayer._instance is None:
                with NoxPlayer._lock:
                    if NoxPlayer._instance is None:
                        NoxPlayer._instance = NoxPlayer(parent=parent, *args)
        except Exception as e:
            log.e(fmt('get_instance error: {0}', e))
            NoxPlayer._instance = False
        finally:
            return NoxPlayer._instance

    def _checkNox(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.ip, self.port))
        sock.setblocking(0)
        sock.settimeout(32)

    def play_item(self, title='', icon='', thumb='', *args, **kwargs):
        self.link = kwargs.get('url')
        return TPlayer.play_item(self, title=title, icon=icon, thumb=thumb, *args, **kwargs)

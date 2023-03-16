# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import json
import socket
import subprocess
import threading
import time
import random
from pathlib import Path
from requests.utils import unquote

# imports
import xbmc
import xbmcgui
from utils import to_bytes

import defines
import logger
import utils

log = logger.Logger(__name__)
sys_platform = defines.platform()['os']


class FlagsControl:

    def __init__(self):
        self.manual_stopped = threading.Event()
        self.switch_source = threading.Event()
        self.channel_stop = threading.Event()

    def clear(self):
        [f.clear() for f in self.__dict__.values()]

    def is_any_flag_set(self):
        return any(f.is_set() for f in self.__dict__.values())

    def log_status(self):
        log.d(''.join([f"{k}: {f.is_set()}; " for k, f in self.__dict__.items()]))

    def autoStop(self):
        self.clear()
        self.switch_source.set()

    def manualStop(self):
        self.clear()
        self.manual_stopped.set()

    def channelStop(self):
        self.clear()
        self.channel_stop.set()


Flags = FlagsControl()


class TPlayer(xbmc.Player):
    _instance = None
    _lock = threading.RLock()

    @classmethod
    def get_instance(cls, parent=None, *args):
        try:
            if cls._instance is None:
                with cls._lock:
                    if cls._instance is None:
                        cls._instance = cls(parent=parent, *args)
        except Exception as e:
            log.e(f'get_instance error: {e}')
            cls._instance = None
        finally:
            return cls._instance

    @classmethod
    def clear_instance(cls):
        if cls._instance is not None:
            with cls._lock:
                cls._instance = None

    def __init__(self, parent=None, *args):
        super(TPlayer, self).__init__()
        self.parent = parent
        self.link = None  # Для передачи ссылки плееру
        self.last_error = None

    def onPlayBackStopped(self):
        log("onPlayBackStopped")

    def onPlayBackEnded(self):
        log('onPlayBackEnded')
        self.autoStop()

    def onPlayBackError(self):
        log('onPlayBackError')
        self.autoStop()

    def onAVStarted(self):
        log('onAVStarted')
        Flags.clear()
        self.parent.hide_main_window()
        self.parent.player.hideStatus()

    def onAVChange(self):
        log('onAVChange')

    def loop(self):
        log.d('loop')
        Flags.clear()
        while self.isPlaying() and not (defines.isCancel() or Flags.is_any_flag_set()):
            try:
                defines.monitor.waitForAbort(0.25)
            except Exception as e:
                log.e(f'ERROR SLEEPING: {e}')
                self.parent.close()
                raise

        self.stop()

    def play_item(self, title='', icon='', thumb='', *args, **kwargs):
        li = xbmcgui.ListItem(title, offscreen=True)
        li.setArt({'icon': icon, 'thumb': thumb})
        if kwargs.get('url'):
            self.link = kwargs['url']
        if not self.link:
            self.parent.showStatus('Нечего проигрывать')
            return
        with defines.progress_dialog_bg(f"Проверка доступности источника для канала {title}") as pd:
            r = defines.request(self.link, method='HEAD', trys=1, timeout=3)
            pd.update(100)
            if not r.ok:
                self.onPlayBackError()
                return

        self.play(self.link, li, windowed=True)
        log.debug(f'play_item {title}')
        self.parent.player.Show()
        self.starttime = time.time()
        self.loop()
        Flags.log_status()

    def end(self):
        log('end player method')
        xbmc.Player.stop(self)
        self.onPlayBackEnded()

    def stop(self):
        log('stop')
        Flags.log_status()
        xbmc.Player.stop(self)

    def autoStop(self):
        log('autoStop')
        Flags.autoStop()
        self.stop()

    def manualStop(self):
        log('manualStop')
        Flags.manualStop()
        self.stop()

    def channelStop(self):
        log('channelStop')
        Flags.channelStop()
        self.stop()


class AcePlayer(TPlayer):
    MODE_TORRENT = 'TORRENT'
    MODE_INFOHASH = 'INFOHASH'
    MODE_RAW = 'RAW'
    MODE_PID = 'PID'
    MODE_NONE = None

    TIMEOUT_FREEZE = utils.str2num(defines.ADDON.getSetting('freeze_timeout'), 20)
    ACE_PATH = Path(defines.ADDON.getSetting('ace_path'))

    _instance = None
    _lock = threading.RLock()

#     @staticmethod
#     def get_instance(parent=None, ipaddr='127.0.0.1', *args):
#         try:
#             if AcePlayer._instance is None:
#                 with AcePlayer._lock:
#                     if AcePlayer._instance is None:
#                         AcePlayer._instance = AcePlayer(parent=parent, ipaddr=ipaddr, *args)
#         except Exception as e:
#             log.e('get_instance error: {0}'.format(uni(e)))
#             AcePlayer._instance = False
#         finally:
#             return AcePlayer._instance

    def __init__(self, parent=None, *args):
        TPlayer.__init__(self, parent=parent, *args)
        log("Init AceEngine")
        if defines.ADDON.getSetting('use_ace') == "false":
            raise Exception("Acestream player is disabled")
        self.quid = 0
        self.ace_engine = ''
        self.aceport = 62062
        self.port_file = ''
        self.sock_thr = None
        self.msg_params = {"last_update": time.time()}
        self.waiting = Waiting()

        log.d(defines.ADDON.getSetting('ip_addr'))
        if defines.ADDON.getSetting('ip_addr'):
            self.server_ip = defines.ADDON.getSetting('ip_addr')
        else:
            self.server_ip = '127.0.0.1'
        if defines.ADDON.getSetting('web_port'):
            self.webport = defines.ADDON.getSetting('webport')
        else:
            self.webport = '6878'

        self.ace_engine = self._getAceEngine_path()
        log.d(f'AceEngine path: "{self.ace_engine}"')

        if sys_platform == "windows":
            self.port_file = self.ace_engine.parent / 'acestream.port'
            log.d(f'AceEngine port file: "{self.port_file}"')
            self.aceport = self._getWinPort()

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
                self.parent.showStatus(f"Подключение к AceEngine ({i})")
                self._sockConnect()
                return True
            except Exception as e:
                log.e(f"Подключение не удалось {e}")
                if not defines.isCancel():
                    defines.monitor.waitForAbort(0.995)
                else:
                    return

    def _getAceEngine_path(self):
        log.d('Считываем путь к ace_engine.exe')
        if AcePlayer.ACE_PATH:
            return Path(AcePlayer.ACE_PATH)
        if sys_platform == 'windows':
            from six.moves import winreg  # @UnresolvedImport
            t = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Software\\ACEStream')  # @UndefinedVariable
            try:
                return Path(winreg.QueryValueEx(t, 'EnginePath')[0])  # @UndefinedVariable
            finally:
                winreg.CloseKey(t)  # @UndefinedVariable
        elif sys_platform == 'linux':
            return Path("acestreamengine")
        else:
            return Path("")

    def _getWinPort(self):
        log.d('Считываем порт')
        for i in range(15):
            if Path(self.port_file).exists():
                return utils.str2int(self.port_file.read_bytes())
            else:
                self.parent.showStatus("Запуск AceEngine ({0})".format(i))
                if not defines.isCancel():
                    xbmc.sleep(995)
                else:
                    break

        return 0

    def _killEngine(self):
        if sys_platform == "windows":
            try:
                log.d(f'Kill "{self.ace_engine.name}"')
                si = subprocess.STARTUPINFO()  # @UndefinedVariable
                si.dwFlags = subprocess.STARTF_USESHOWWINDOW  # @UndefinedVariable
                si.wShowWindow = subprocess.SW_HIDE  # @UndefinedVariable

                subprocess.call(["taskkill", "/F", "/IM", self.ace_engine.name], shell=False, startupinfo=si)
                log.d(f'Remove "{self.port_file}"')
                self.port_file.unlink(missing_ok=True)
            except Exception as e:
                log.d(f"_killEngine error: {e}")

    def _startEngine(self):
        acestream_params = ["--live-cache-type", "memory"]
        if self.server_ip == '127.0.0.1':
            if sys_platform == 'windows':
                try:
                    self._killEngine()

                    log('try to start AceEngine for windows')
                    self.parent.showStatus("Запуск AceEngine")
                    p = subprocess.Popen([self.ace_engine] + acestream_params)
                    log.d(f'pid = {p.pid}')

                    self.aceport = self._getWinPort()
                    if self.aceport <= 0:
                        return

                except Exception as e:
                    log.e(f'Cannot start AceEngine {e}')
                    return
            elif sys_platform == 'linux':
                log('try to start AceEngine for linux')
                acestream_params += ["--client-console"]
                try:
                    self.parent.showStatus("Запуск acestreamengine")
                    p = subprocess.Popen([self.ace_engine] + acestream_params)
                    log.d(f'pid = {p.pid}')
                except Exception as e:
                    log.e(f'Cannot start AceEngine {e}')
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
        #             r = defines.request("http://{url}/xbmc_get_key.php".format(url=defines.API_MIRROR, trys=1),
        #                                 params={'key': key})
        #             r.raise_for_status()
        #             return r.text
        #         except:
        import hashlib
        pkey = 'n51LvQoTlJzNGaFxseRK-uvnvX-sD4Vm5Axwmc4UcoD-jruxmKsuJaH0eVgE'
        sha1 = hashlib.sha1()
        sha1.update(to_bytes(key + pkey))
        key = sha1.hexdigest()
        pk = pkey.split('-')[0]
        return f"{pk}-{key}"

    def _connectToTS(self):
        log.d(f'Подключение к AceEngine {self.server_ip} {self.aceport}')
        for t in range(3):
            try:
                log.d(f"Попытка подлючения ({t})")
                self._sockConnect()
                break
            except Exception as e:
                if self._startEngine():
                    if not self._checkConnect():
                        msg = f'Ошибка подключения к AceEngine: {e}'
                        log.f(msg)
                        self.parent.showStatus('Ошибка подключения к AceEngine!')
                    else:
                        break
                else:
                    msg = "Не удалось запустить AceEngine!"
                    self.parent.showStatus(msg)

                if not defines.isCancel():
                    defines.monitor.waitForAbort(0.995)
                else:
                    raise Exception('Cancel')
        else:
            msg = 'Ошибка подключения к AceEngine'
            self.parent.showStatus(msg)
            raise Exception(msg)

        log.d('Все ок')
        # Общаемся
        try:
            msg = self._send_command('HELLOBG version=4', TSMessage.HELLOTS)
            if msg:
                if not msg.getParams().get('key'):
                    raise IOError('Incorrect msg from AceEngine')
                ace_version = msg.getParams().get('version')
                if ace_version < '3':
                    raise ValueError("It's necessary to update AceStream")

                msg = self._send_command('READY key=' + self._get_key(msg.getParams().get('key')), TSMessage.AUTH)
                if msg:
                    if utils.str2int(msg.getParams()) == 0:
                        log.w('Пользователь не зарегистрирован')
                else:
                    raise IOError('Incorrect msg from AceEngine')

        except IOError as io:
            log.e(f'Error while auth: {io}')
            self.last_error = io
            self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
            return
        except ValueError as ve:
            log.e(f'AceStream version error: {ve}')
            self.last_error = ve
            self.parent.showStatus("Необходимо обновить AceStream до версии 3")
            return
        except Exception as e:
            log.e(f'_connectToTS error: {e}')

        log.d('End Init AceEngine')
        self.parent.hideStatus()

    def _send_command(self, cmd, wait_msg=None):
        """
        Send command to aceEngine and wait a message if wait_msg given
        :cmd: Command to send
        :wai_msg: Message for wait (START, AUTH, etc)
        :return: TSMessage object if wait_msg is given and waiting was successfuly, else
                if wait_msg is not given and sending command was successfuly then return True else None
        """
        try:
            if not (self.sock_thr and self.sock_thr.is_active()):
                if cmd not in (TSMessage.STOP, TSMessage.SHUTDOWN):
                    self._createThread()
                else:
                    return
            # Waiting message if need
            log.d(f'>> "{cmd}"')
            if wait_msg:
                with self.waiting.lock:
                    log.d(f'wait message: {wait_msg}')
                    try:
                        self.waiting.msg = wait_msg
                        self.waiting.event.clear()
                        self.waiting.abort.clear()
                        self.sock.send(to_bytes(cmd + '\r\n'))
                        for t in range(AcePlayer.TIMEOUT_FREEZE * 3):  # @UnusedVariable
                            log.d(f"waiting message {wait_msg} ({t})")
                            if not self.waiting.msg or self.sock_thr.error or defines.isCancel():
                                raise ValueError(f'Abort waiting message: "{wait_msg}"')
                            if self.waiting.wait(1):
                                return self.waiting.msg

                        self.parent.showStatus("Ошибка ожидания. Операция прервана")
                        raise ValueError('AceEngine is freeze')

                    except Exception as e:
                        log.e(f'_wait_message error: {e}')
                        self.waiting.msg = None
                        if not Flags.manual_stopped.is_set():
                            self.autoStop()
                        return

            else:
                self.sock.send(to_bytes(cmd + '\r\n'))
                return True

        except Exception as e:
            log.e(f'_send_command error: "{e}" cmd: "{cmd}"')

        if self.sock_thr and self.sock_thr.is_active():
            self.sock_thr.end()

    def _wait_message(self, msg):
        """
        Wait message
        :msg: Message for wait (START, AUTH, etc)
        :return: TSMessage object if wait was successfully, else None
        """
        with self.waiting.lock:
            log.d(f'wait message: {msg}')
            try:
                self.waiting.msg = msg
                self.waiting.event.clear()
                for t in range(AcePlayer.TIMEOUT_FREEZE * 3):  # @UnusedVariable
                    log.d(f"waiting message {msg} ({t})")
                    if not self.waiting.msg or self.sock_thr.error or defines.isCancel():
                        raise ValueError(f'Abort waiting message: "{msg}"')
                    if self.waiting.event.wait(1):
                        return self.waiting.msg

                self.parent.showStatus("Ошибка ожидания. Операция прервана")
                raise ValueError('AceEngine is freeze')

            except Exception as e:
                log.e(f'_wait_message error: {e}')
                self.waiting.msg = None
                if not Flags.manual_stopped.is_set():
                    self.autoStop()

    def _createThread(self):
        self.sock_thr = SockThread(self.sock)
        self.sock_thr.state_handler = self._stateHandler
        self.sock_thr.owner = self
        self.sock_thr.start()

    def _load_torrent(self, torrent, mode):
        log(f"Load Torrent: {torrent}, mode: {mode}")
        cmdparam = ''
        if mode != AcePlayer.MODE_PID:
            cmdparam = ' 0 0 0'
        self.quid = str(random.randint(0, 0x7fffffff))
        comm = f'LOADASYNC {self.quid} {mode} {torrent} {cmdparam}'
        self.parent.showStatus("Загрузка торрента")

        if self._send_command(comm):
            msg = self._send_command(comm, TSMessage.LOADRESP)
            if msg:
                try:
                    log.d(f'_load_torrent - {msg.getType()}')
                    log.d('Compile file list')

                except Exception as e:
                    log.e(f'_load_torrent error: {e}')
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
                        self.msg_params['prebuf'] = 0

                    elif _descr[0] == 'prebuf':
                        if _descr[1] != self.msg_params.get('prebuf', 0):
                            self.msg_params['last_update'] = state.getTime()
                            self.msg_params['prebuf'] = _descr[1]
                            log.d('_stateHandler: Пытаюсь показать состояние')
                            self.parent.showStatus(f"Пребуферизация {self.msg_params['prebuf']}")
                            self.parent.player.showStatus(f"Пребуферизация {self.msg_params['prebuf']}")

                        if time.time() - self.msg_params['last_update'] >= AcePlayer.TIMEOUT_FREEZE:
                            log.w('AceEngine is freeze')
                            self.autoStop()

                    elif _descr[0] == 'check':
                        log.d(f'_stateHandler: Проверка {_descr[1]}')
                        self.parent.showStatus(f'Проверка {_descr[1]}')
                    #                     elif _descr[0] == 'dl':
                    #                         self.parent.showInfoStatus('Total:%s DL:%s UL:%s' % (_descr[1], _descr[3], _descr[5]))
                    elif _descr[0] == 'buf':
                        # self.parent.showStatus('Буферизация: %s DL: %s UL: %s' % (_descr[1],
                        # _descr[5], _descr[7])) @IgnorePep8

                        if _descr[1] != self.msg_params.get('buf', 0):
                            self.msg_params['last_update'] = state.getTime()
                            self.msg_params['buf'] = _descr[1]
                        #                             self.parent.player.showStatus('Буферизация {0}'.format(self.msg_params['value']))
                        if time.time() - self.msg_params['last_update'] >= AcePlayer.TIMEOUT_FREEZE:
                            self.parent.player.showStatus(f"Пребуферизация {self.msg_params['buf']}")
                            log.w('AceEngine is freeze')
                            self.autoStop()
            #                     elif _descr[0] == 'dl':
            #                         if _descr[8] != self.msg_params.get('downloaded', 0):
            #                             self.msg_params['last_update'] = state.getTime()
            #                             self.msg_params['downloaded'] = _descr[8]
            #                         if time.time() - self.msg_params['last_update'] >= 10:
            #                             log.w('AceEngine is freeze')
            #                             self.autoStop()

            #                         self.parent.showInfoStatus('Buf:%s DL:%s UL:%s' % (_descr[1], _descr[5], _descr[7]))
            #                     else:
            #                         self.parent.showInfoStatus('%s' % _params)
            elif state.getType() in (TSMessage.RESUME, TSMessage.PAUSE, TSMessage.START):
                self.msg_params['value'] = 0
            #                 self.msg_params['downloaded'] = 0

            elif state.getType() == TSMessage.EVENT:
                if state.getParams() == 'getuserdata':
                    self._send_command(f'USERDATA [{{"gender": {defines.GENDER + 1}}} {{"age": {defines.AGE + 1}}}]')
                elif state.getParams().startswith('showdialog'):
                    _parts = state.getParams().split()
                    self.parent.showStatus('{0}: {1}'.format(unquote(_parts[2].split('=')[1]),
                                                             unquote(_parts[1].split('=')[1])))
            elif state.getType() == TSMessage.ERROR:
                self.parent.showStatus(state.getParams())

            elif state.getType() == TSMessage.STOP:
                self.waiting.abort.set()

            elif state.getType() == TSMessage.STATE:
                _params = state.getParams()
                _param = utils.str2int(_params)
                if _param == 0:
                    self.waiting.abort.set()

        except Exception as e:
            log.e(f'_stateHandler error: "{e}"')
        finally:
            try:
                if self.waiting.msg == state.getType():
                    self.waiting.msg = state
                    self.waiting.event.set()

            except Exception as e:
                log.e(f'_stateHandler error: "{e}"')

    def play_item(self, title='', icon='', thumb='', *args, **kwargs):
        if self.last_error:
            return
        url = kwargs.get('url')
        mode = kwargs.get('mode')
        index = kwargs.get('index', 0)
        if not url:
            self.parent.showStatus('Нечего проигрывать')
            return
        oparams = '0 0 0' if mode != AcePlayer.MODE_PID else ''
        comm = f'START {mode} {url} {index} {oparams}'
        log.d("Запуск торрента")
        xbmc.sleep(4)
        self.parent.showStatus("Запуск торрента")
        msg = self._send_command(comm, TSMessage.START)
        if msg:
            try:
                _params = msg.getParams()
                if not _params.get('url'):
                    self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
                    raise Exception(f'Incorrect msg from AceEngine {msg.getType()}')

                self.link = _params['url'].replace('127.0.0.1', self.server_ip).replace('6878', self.webport)
                log.d(f'Преобразование ссылки: {self.link}')
                TPlayer.play_item(self, title, icon, thumb)
            except Exception as e:
                log.e(f'play_item error: {e}')
                self.last_error = e
                self.parent.showStatus("Ошибка. Операция прервана")
        else:
            self.last_error = 'Incorrect msg from AceEngine'
            log.e(self.last_error)
            self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")

    def end(self):
        self.link = None
        TPlayer.end(self)
        if self._send_command(TSMessage.STOP):
            self._send_command(TSMessage.SHUTDOWN)
        self.waiting.msg = None
        self.last_error = None
        if self.sock_thr:
            self.sock_thr.end()
            self.sock_thr = None
        self.sock.close()

    def stop(self):
        self.link = None
        TPlayer.stop(self)
        self._send_command(TSMessage.STOP)
        self.waiting.msg = None
        if self.sock_thr:
            self.sock_thr.end()
            self.sock_thr.join()
            self.sock_thr = None
        self.last_error = None


class Waiting:

    def __init__(self):
        self.event = threading.Event()
        self.lock = threading.Lock()
        self.abort = threading.Event()
        self.msg = None

    def wait(self, timeout):
        if self.abort.is_set():
            raise Exception("Abort waiting")
        self.event.wait(timeout)
        return self.event.is_set()


class TSMessage:
    ERROR = 'ERROR'
    HELLOTS = 'HELLOTS'
    AUTH = 'AUTH'
    LOADRESP = 'LOADRESP'
    STATUS = 'STATUS'
    STATE = 'STATE'
    START = 'START'
    STOP = 'STOP'
    EVENT = 'EVENT'
    PAUSE = 'PAUSE'
    RESUME = 'RESUME'
    SHUTDOWN = 'SHUTDOWN'
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
        log.d(f"run SockThread{self.ident}")
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
                            log.d(f'<< "{cmd}"')
                            self._constructMsg(cmd)
                    self.lastRecv = ''
            except Exception as e:
                self.isRecv = True
                self.end()
                self.error = e
                log.e(f'RECV THREADING {e}')
                _msg = TSMessage(TSMessage.ERROR)
                _msg.params = 'Ошибка соединения с AceEngine'
                self.state_handler(_msg)
        log.d('Exit from sock thread')
        self.error = None

    def _constructMsg(self, strmsg):
        strmsg = strmsg
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
        if not defines.ADDON.getSettingBool('use_nox'):
            raise Exception("Noxbit player is disabled")
        self.ip = defines.ADDON.getSetting('nox_ip')
        self.port = defines.ADDON.getSettingInt('nox_port')
        self._checkNox()

    def _checkNox(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.ip, self.port))
        sock.setblocking(0)
        sock.settimeout(32)

    def play_item(self, title='', icon='', thumb='', *args, **kwargs):
        self.link = kwargs.get('url')
        TPlayer.play_item(self, title=title, icon=icon, thumb=thumb, *args, **kwargs)

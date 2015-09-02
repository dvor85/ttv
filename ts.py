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
import json
import urllib
import copy

import defines

from adswnd import AdsForm

# defines
DEFAULT_TIMEOUT = 122

LogToXBMC = defines.Logger('TSEngine')

# classes
class TSengine(xbmc.Player):
    MODE_TORRENT = 'TORRENT'
    MODE_INFOHASH = 'INFOHASH'
    MODE_RAW = 'RAW'
    MODE_PID = 'PID'
    MODE_NONE = None
    
    def __init__(self, parent=None, ipaddr='127.0.0.1'):
        LogToXBMC("Init TSEngine")
        self.last_error = None
        self.quid = 0
        self.torrent = ''
        self.amalker = False
        self.parent = parent
        self.stream = False
        self.playing = False
        self.ace_engine = ''
        self.port_file = ''
        self.paused = False
        self.closed = False
        self.trys = 0
        self.thr = None
       
        LogToXBMC(defines.ADDON.getSetting('ip_addr'), xbmc.LOGDEBUG)
        if defines.ADDON.getSetting('ip_addr'):
            self.server_ip = defines.ADDON.getSetting('ip_addr')
        else:
            self.server_ip = ipaddr
            defines.ADDON.setSetting('ip_addr', ipaddr)
        if defines.ADDON.getSetting('web_port'):
            self.webport = defines.ADDON.getSetting('webport')
        else:
            self.webport = '6878'
        if defines.ADDON.getSetting('port'):
            self.aceport = int(defines.ADDON.getSetting('port'))
        else:
            self.aceport = 62062

        if not defines.ADDON.getSetting('age'):
            defines.ADDON.setSetting('age', '1')
        if not defines.ADDON.getSetting('gender'):
            defines.ADDON.setSetting('gender', '1')
        try:
            LogToXBMC('Connect to AceEngine', xbmc.LOGDEBUG)
            self.connectToTS()
        except Exception, e:
            LogToXBMC('ERROR Connect to AceEngine: %s' % e, xbmc.LOGFATAL)
            return

    def onPlayBackStopped(self):
        LogToXBMC('onPlayBackStopped')
        if not self.amalker and self.playing:
            LogToXBMC('STOP', xbmc.LOGDEBUG)
            self.parent.player.close()
            self.tsstop()
        elif self.amalker:
            self.parent.amalkerWnd.close()
        else:
            LogToXBMC("STOP", xbmc.LOGDEBUG)
            self.tsstop()

    def onPlayBackEnded(self):
        LogToXBMC('onPlayBackEnded')
        self.onPlayBackStopped()

    def onPlayBackStarted(self):
        pass
        LogToXBMC('%s %s %s' % (xbmcgui.getCurrentWindowId(), self.amalker, self.getPlayingFile()), xbmc.LOGDEBUG)
        if not self.amalker:
            self.parent.player.show()
            pass
        elif self.amalker:
            pass
            LogToXBMC('SHOW ADS Window', xbmc.LOGDEBUG)
            self.parent.amalkerWnd.show()
            LogToXBMC('END SHOW ADS Window', xbmc.LOGDEBUG)

    def getAceEngine_exe(self):
        LogToXBMC('Считываем путь к ace_engine.exe', xbmc.LOGDEBUG)      
        import _winreg              
        t = None
        try:
            LogToXBMC('ACEStream', xbmc.LOGDEBUG)
            t = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, 'Software\\ACEStream')
            return _winreg.QueryValueEx(t , 'EnginePath')[0]           
            
        except Exception, e:
            LogToXBMC('Error Opening acestream.port %s' % e, xbmc.LOGERROR)
            return ''
        finally:
            if t:    
                _winreg.CloseKey(t)

    def connectToTS(self):
        try:
            LogToXBMC('Подключение к AceEngine %s %s ' % (self.server_ip, self.aceport))
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.server_ip, self.aceport))
            self.sock.setblocking(0)
            self.sock.settimeout(32)
        except Exception, e:
            import subprocess
            LogToXBMC('Ошибка подключения %s' % e, xbmc.LOGWARNING)
            acestream_params = ["--live-cache-type", defines.LIVE_CACHE_TYPE]
            if defines.tryStringToInt(defines.LIVE_CACHE_SIZE) > 0:
                acestream_params += ["--live-cache-size", defines.LIVE_CACHE_SIZE]
            if defines.LIVE_CACHE_TYPE == 'disk' and defines.CACHE_DIR != '':
                acestream_params += ['--cache-dir', defines.CACHE_DIR]
            acestream_params += ["--client-{0}".format(defines.ACE_CLIENT)]
            
            if sys.platform.startswith('win') and self.server_ip == '127.0.0.1':
                try:
                    if self.port_file != '' and os.path.exists(self.port_file):
                        os.remove(self.port_file)
                   
                    self.ace_engine = self.getAceEngine_exe()
                    ace_console = os.path.join(os.path.dirname(self.ace_engine), "ace_console.exe")
                    if os.path.isfile(ace_console):
                        self.ace_engine = ace_console 
                    LogToXBMC("AceEngine path: {0}".format(self.ace_engine.encode('utf-8'), xbmc.LOGDEBUG))       
                       
                    self.port_file = os.path.join(os.path.dirname(self.ace_engine), 'acestream.port')
                    LogToXBMC('Пытаюсь открыть acestream.port %s' % self.port_file.encode('utf-8'))
                    if not os.path.exists(self.port_file):
                        LogToXBMC('Запуск AceEngine path:%s' % self.ace_engine.encode("utf-8"), xbmc.LOGDEBUG)
                        if self.parent: self.parent.showStatus("Запуск AceEngine")
                        i = 0
                        subprocess.Popen([self.ace_engine] + acestream_params)
                        while not os.path.exists(self.port_file):
                            i += 1
                            if self.parent: self.parent.showStatus("Запуск AceEngine")
                            if i >= 30:
                                msg = 'Невозможно запустить AceEngine'
                                LogToXBMC(msg, xbmc.LOGERROR)
                                raise Exception(msg)
                            xbmc.sleep(986)
                    if self.parent: 
                        self.parent.hideStatus()
                    LogToXBMC('Считываем порт', xbmc.LOGDEBUG)
                    with open(self.port_file, 'r') as gf:
                        self.aceport = int(gf.read())
                    defines.ADDON.setSetting('port', str(self.aceport))
                    self.connectToTS()
                    return
                except Exception, e:
                    LogToXBMC('connectToTS: %s' % e, xbmc.LOGFATAL)
                    return
            else:                
                try:
                    if self.parent: 
                        self.parent.showStatus("Запуск acestreamengine")                    
                    subprocess.Popen(["acestreamengine"] + acestream_params)
                    i = 0
                    while True:
                        try:
                            i += 1
                            if i >= 30:
                                break
                            LogToXBMC("Попытка подлючения")
                            if self.parent: self.parent.showStatus("Запуск acestreamengine %s" % i)
                            self.sock.connect((self.server_ip, self.aceport))
                            if self.parent: self.parent.hideStatus()
                            xbmc.sleep(1000)
                            break
                        except Exception, e:
                            LogToXBMC("Подключение не удалось %s" % e, xbmc.LOGERROR)
                            xbmc.sleep(995)
                            continue
                    if i > 30:
                        msg = TSMessage()
                        msg.type = TSMessage.ERROR
                        msg.params = "Невозможно запустить acestreamengine"
                        LogToXBMC(msg.params, xbmc.LOGERROR)
                        self.showState(msg)
                        return
                    
                except:
                    LogToXBMC('Cannot start TS', xbmc.LOGFATAL)
                    return
        LogToXBMC('Все ок', xbmc.LOGDEBUG)
        self.trys = 0
        self.thr = SockThread(self.sock)
        self.thr.state_method = self.showState
        self.thr.owner = self
        self.thr.start()
        # Общаемся
        self.sendCommand('HELLOBG version=4')
        self.Wait(TSMessage.HELLOTS)
        msg = self.thr.getTSMessage()
        if msg.getType() == TSMessage.HELLOTS and not msg.getParams().has_key('key'):
            self.last_error = 'Incorrect msg from TS'
            if self.parent: self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
            LogToXBMC('Incorrect msg from TS %s' % msg.getType(), xbmc.LOGERROR)
            self.end()
            return
        
        reqk = defines.GET("http://api.torrent-tv.ru/xbmc_get_key.php?key=" + msg.getParams()['key'])
        
        self.thr.msg = TSMessage()
        LogToXBMC('Send READY', xbmc.LOGDEBUG)
        self.sendCommand('READY key=' + reqk)
        self.Wait(TSMessage.AUTH)
        msg = self.thr.getTSMessage()
        if msg.getType() == TSMessage.AUTH:
            if msg.getParams() == '0':
                self.last_error = 'Пользователь не зарегестрирован'
                LogToXBMC(self.last_error, xbmc.LOGFATAL)                
                self.end()
                return
        else:
            self.last_error = 'Incorrect msg from AceEngine'
            LogToXBMC('Incorrect msg from AceEngine %s' % msg.getType(), xbmc.LOGERROR)
            if self.parent: self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
            self.end()
            return

        self.thr.msg = TSMessage()
        LogToXBMC('End Init AceEngine', xbmc.LOGDEBUG)
        if self.parent: self.parent.hideStatus()
        
    
        
    def sendCommand(self, cmd):
        try:
            LogToXBMC('Send command %s' % cmd, xbmc.LOGDEBUG)
            if not self.thr.active:
                self.createThread()
            self.sock.send(cmd + '\r\n')
        except Exception, e:
            try:
                self.trys = self.trys + 1
                if self.trys >= 3:
                    return
                self.connectToTS()
                self.sendCommand(cmd)
            except Exception, e:
                self.thr.active = False
                self.parent.close()
                LogToXBMC('ERROR Send command: %s' % e, xbmc.LOGERROR)
    
    def Wait(self, msg):
        a = 0
        try:
            while self.thr.getTSMessage().getType() != msg and not self.thr.error and not self.closed:
                xbmc.sleep(DEFAULT_TIMEOUT)
                if not self.stream: xbmc.sleep(DEFAULT_TIMEOUT)
                a = a + 1
                if a >= 249:
                    LogToXBMC('AceEngine is freeze', xbmc.LOGWARNING)
                    if self.parent: self.parent.showStatus("Ошибка ожидания. Операция прервана")
                    self.tsstop()
                    raise Exception('AceEngine is freeze')
                    return
        except:
            self.tsstop()
    
    def createThread(self):
        self.thr = SockThread(self.sock)
        self.thr.active = True
        self.thr.state_method = self.showState
        self.thr.owner = self
        self.thr.start()

    def load_torrent(self, torrent, mode):

        cmdparam = ''
        self.mode = mode
        if mode != TSengine.MODE_PID:
            cmdparam = ' 0 0 0'
        self.quid = str(random.randint(0, 0x7fffffff))
        self.torrent = torrent
        comm = 'LOADASYNC ' + self.quid + ' ' + mode + ' ' + torrent + cmdparam
        if self.parent: self.parent.showStatus("Загрузка торрента")
        self.tsstop()
        
        self.sendCommand(comm)
        self.Wait(TSMessage.LOADRESP)
        msg = self.thr.getTSMessage()
        LogToXBMC('load_torrent - %s' % msg.getType())
        if msg.getType() == TSMessage.LOADRESP:
            try:
                LogToXBMC('Compile file list', xbmc.LOGDEBUG)
                jsonfile = msg.getParams()['json']
                if not jsonfile.has_key('files'):
                    self.parent.showStatus(jsonfile['message'])
                    self.last_error = Exception(jsonfile['message'])
                    LogToXBMC('Compile file list %s' % self.last_error, xbmc.LOGERROR)
                    return
                self.count = len(jsonfile['files'])
                self.files = {}
                for file in jsonfile['files']:
                    self.files[file[1]] = urllib.unquote_plus(urllib.quote(file[0]))
                LogToXBMC('End Compile file list', xbmc.LOGDEBUG)
            except Exception, e:
                LogToXBMC(e, xbmc.LOGERROR)
                self.last_error = e
                self.end()
        else:
            self.last_error = 'Incorrect msg from AceEngine'
            if self.parent: self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
            LogToXBMC('Incorrect msg from AceEngine %s' % msg.getType(), xbmc.LOGFATAL)
            self.tsstop()
            return

        LogToXBMC("Load Torrent: %s, mode: %s" % (torrent, mode), xbmc.LOGDEBUG)
        if self.parent: self.parent.hideStatus()

    def showState(self, state):
        if state.getType() == TSMessage.STATUS and self.parent:
            _params = state.getParams()
            if _params.has_key('main'):
                _descr = _params['main'].split(';')
                if _descr[0] == 'prebuf':
                    LogToXBMC('showState: Пытаюсь показать состояние')
                    self.parent.showStatus('Пребуферизация %s' % _descr[1])
                elif _descr[0] == 'check':
                    LogToXBMC('showState: Проверка %s' % _descr[1], xbmc.LOGDEBUG)
                    self.parent.showStatus('Проверка %s' % _descr[1])
                elif _descr[0] == 'dl':
                    self.parent.showInfoStatus('Total:%s DL:%s UL:%s' % (_descr[1], _descr[3], _descr[5]))
                elif _descr[0] == 'buf':
                    self.parent.showInfoStatus('Buf:%s DL:%s UL:%s' % (_descr[1], _descr[5], _descr[7]))
                else:
                    self.parent.showInfoStatus('%s' % _params)
        elif state.getType() == TSMessage.EVENT:
            if state.getParams() == 'getuserdata':
                self.sendCommand('USERDATA [{"gender": %s}, {"age": %s}]' % (int(defines.ADDON.getSetting('gender')) + 1, int(defines.ADDON.getSetting('age')) + 1))
        elif state.getType() == TSMessage.ERROR:
            self.parent.showStatus(state.getParams())
    
    def play_url_ind(self, index=0, title='', icon=None, thumb=None, torrent=None, mode=None):
        if self.last_error:
            return
        if torrent or self.torrent == '':
            self.torrent = torrent
            self.mode = mode
        if not self.torrent or self.torrent == '':
            self.parent.showStatus('Нечего проигрывать')
            return
        spons = ''
        if self.mode != TSengine.MODE_PID:
            spons = ' 0 0 0'
        comm = 'START ' + self.mode + ' ' + self.torrent + ' ' + str(index) + spons
        LogToXBMC("Запуск торрента")
        self.stop()
        xbmc.sleep(4)
        self.sendCommand(comm)
        if self.parent: self.parent.showStatus("Запуск торрента")
        self.Wait(TSMessage.START)
        msg = self.thr.getTSMessage()
        if msg.getType() == TSMessage.START:
            try:
                _params = msg.getParams()
                if not _params.has_key('url'):
                    if self.parent: self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
                    raise Exception('Incorrect msg from AceEngine %s' % msg.getType())

                self.amalker = _params.has_key('ad') and not _params.has_key('interruptable')
                self.link = _params['url'].replace('127.0.0.1', self.server_ip).replace('6878', self.webport)
                LogToXBMC('Преобразование ссылки: %s' % self.link, xbmc.LOGDEBUG)
                self.title = title
                self.icon = icon
                self.playing = True
                
                self.thr.msg = TSMessage()
                if self.amalker:
                    self.parent.showStatus('Рекламный ролик')
                #    self.parent.player.doModal()
                # else:
                #    self.parent.amalker.show()
                LogToXBMC('Первый запуск. Окно = %s. Реклама = %s' % (xbmcgui.getCurrentWindowId(), self.amalker), xbmc.LOGDEBUG)
                self.icon = icon
                self.thumb = thumb
                lit = xbmcgui.ListItem(title, iconImage=icon, thumbnailImage=thumb)
                self.play(self.link, lit, windowed=True)
                self.playing = True
                self.paused = False
                self.loop()
            except Exception, e:
                LogToXBMC(e, xbmc.LOGERROR)
                self.last_error = e
                if self.parent: self.parent.showStatus("Ошибка. Операция прервана")
                self.tsstop()
        else:
            self.last_error = 'Incorrect msg from AceEngine %s' % msg.getType()
            LogToXBMC(self.last_error, xbmc.LOGERROR)
            if self.parent: self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
            self.tsstop()

    def loop(self):
        # xbmc.sleep(500)
        while self.playing:
            # if not self.isPlayingVideo():
            #    break

            if self.isPlayingVideo() and self.amalker and (self.getTotalTime() - self.getTime()) < 0.5:
                self.parent.amalkerWnd.close()
                break
            try:
                if xbmc.abortRequested:
                    LogToXBMC("XBMC Shutdown")
                    break
                xbmc.sleep(250)
                # if not self.isPlaying() and self.playing:
                #    self.tsstop()
                #    break

            except:
                LogToXBMC('ERROR SLEEPING', xbmc.LOGERROR)
                self.parent.close()
                return
            

        if self.amalker:
            self.sendCommand('PLAYBACK ' + self.play_url + ' 100')
            self.Wait(TSMessage.START)
            msg = self.thr.getTSMessage()
            if msg.getType() == TSMessage.START:
                try:
                    _params = msg.getParams()
                    if not _params.has_key('url'):
                        raise Exception('Incorrect msg from AceEngine %s' % msg.getType())
                    if _params.has_key('stream') and _params['stream'] == '1':
                        self.stream = True
                    else:
                        self.stream = False

                    self.play_url = _params['url'].replace('127.0.0.1', self.server_ip).replace('6878', self.webport)
                    self.amalker = _params.has_key('ad') and not _params.has_key('interruptable')
                    if self.amalker:
                        self.parent.showStatus('Рекламный ролик')

                    lit = xbmcgui.ListItem(self.title, iconImage=self.icon, thumbnailImage=self.thumb)
                    self.play(self.play_url, lit, windowed=True)
                    self.paused = False
                    self.loop()
                except Exception, e:
                    LogToXBMC(e, xbmc.LOGERROR)
                    self.last_error = e
                    if self.parent: self.parent.showStatus("Ошибка. Операция прервана")
                    self.tsstop()
            else:
                self.last_error = 'Incorrect msg from AceEngine %s' % msg.getType()
                if self.parent: self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
                LogToXBMC(self.last_error, xbmc.LOGERROR)
                self.tsstop()

    def end(self):
        self.sendCommand('STOP')
        self.sendCommand('SHUTDOWN')
        self.last_error = None
        LogToXBMC("Request to close connection")
        if self.thr:
            self.thr.msg = TSMessage()
            self.thr.active = False
        self.playing = False
        self.paused = False
        self.sock.close()

    def tsstop(self):
        self.sendCommand('STOP')
        self.playing = False
        if self.thr:
            self.thr.active = False
            self.thr.join()
        self.last_error = None
        self.paused = False

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
        LogToXBMC('Init SockThread')
        threading.Thread.__init__(self)
        self.daemon = True
        self.sock = _sock
        self.buffer = 65025
        self.isRecv = False
        self.lastRecv = ''
        self.lstCmd = ''
        self.active = True
        self.error = None
        self.msg = TSMessage()
        self.state_method = None
        self.owner = None

    def run(self):
        LogToXBMC('Start SockThread')
        while self.active and not self.error and not xbmc.abortRequested:
            try:
                xbmc.sleep(32)
                self.lastRecv = self.lastRecv + self.sock.recv(self.buffer)
                if self.lastRecv.find('\r\n') > -1:
                    cmds = self.lastRecv.split('\r\n')
                    for cmd in cmds:                        
                        if len(cmd.replace(' ', '')) > 0 and self.active and not self.error and not xbmc.abortRequested:
                            LogToXBMC('RUN Получена комманда = ' + cmd, xbmc.LOGDEBUG)
                            self._constructMsg(cmd)
                    self.lastRecv = ''
            except Exception, e:
                self.isRecv = True
                self.active = False
                self.error = e
                LogToXBMC('RECV THREADING %s' % e, xbmc.LOGERROR)
                _msg = TSMessage()
                _msg.type = TSMessage.ERROR
                _msg.params = 'Ошибка соединения с TS'
                self.state_method(_msg)
                # self.owner.end()
                # self.owner.connectToTS()
                # self.owner.parent.close()
        LogToXBMC('Close from thread')
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
            LogToXBMC(strmsg, xbmc.LOGDEBUG)
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
                LogToXBMC('I DONT KNOW HOW IT PROCESS %s' % strmsg, xbmc.LOGWARNING)
            return
        elif _msg == TSMessage.STATE:
            if self.state_method: 
                self.state = TSMessage()
                self.state.setType(TSMessage.STATE)
                self.state.setParams(strmsg[posparam + 1:])
                self.state_method(self.state)
            return
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
            LogToXBMC(strmsg, xbmc.LOGDEBUG)
            if _strparams.__len__() >= 2:
                LogToXBMC('%s' % _strparams, xbmc.LOGDEBUG)
                _params['url'] = _strparams[0].split("=")[1].replace("%3A", ":")
                prms = _strparams[1:]
                for prm in prms:
                    sprm = prm.split('=')
                    _params[sprm[0]] = sprm[1]
                    
            else:
                _params['url'] = _strparams[0].split("=")[1].replace("%3A", ":")
            self.msg.setType(TSMessage.START)
            self.msg.setParams(_params)
        elif _msg == TSMessage.PAUSE:
            msg = TSMessage()
            msg.setType(TSMessage.PAUSE)
            LogToXBMC("GET PAUSE", xbmc.LOGDEBUG)
            self.state_method(msg)
        elif _msg == TSMessage.RESUME:
            msg = TSMessage()
            msg.setType(TSMessage.RESUME)
            LogToXBMC("GET RESUME", xbmc.LOGDEBUG)
            self.state_method(msg)


    def getTSMessage(self):
        res = copy.deepcopy(self.msg)
        return res

    def end(self):
        self.active = False

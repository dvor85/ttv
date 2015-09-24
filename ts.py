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
import json

from adswnd import AdsForm

# defines
DEFAULT_TIMEOUT = 122

log = defines.Logger('TSEngine')

# classes
class TSengine(xbmc.Player):
    MODE_TORRENT = 'TORRENT'
    MODE_INFOHASH = 'INFOHASH'
    MODE_RAW = 'RAW'
    MODE_PID = 'PID'
    MODE_NONE = None
    
    def __init__(self, parent=None, ipaddr='127.0.0.1'):
        log.d("Init TSEngine")
        self.last_error = None
        self.quid = 0
        self.torrent = ''
        self.amalker = False
        self.parent = parent
        self.stream = False
        self.playing = False
        self.ace_engine = ''
        self.port_file = ''
        self.trys = 0
        self.thr = None
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
        if defines.ADDON.getSetting('port'):
            self.aceport = int(defines.ADDON.getSetting('port'))
        else:
            self.aceport = 62062

        if not defines.ADDON.getSetting('age'):
            defines.ADDON.setSetting('age', '1')
        if not defines.ADDON.getSetting('gender'):
            defines.ADDON.setSetting('gender', '1')
        try:
            log.d('Connect to AceEngine')
            self.connectToTS()
        except Exception, e:
            log.f('ERROR Connect to AceEngine: %s' % e)
            raise
        
    def getPlayingFile(self):
        if self.isPlaying():
            if self.link:
                return self.link
        return xbmc.Player.getPlayingFile(self)
    
    def isPlaying(self):
        return self.playing or xbmc.Player.isPlaying(self) 

    def onPlayBackStopped(self):
        log.d('onPlayBackStopped')
        if not self.amalker and self.isPlaying():
            self.stop()
            self.parent.player.close()            
        elif self.amalker:
            self.parent.amalkerWnd.close()
        else:
            self.stop()              
        xbmc.Player.onPlayBackStopped(self)

    def onPlayBackEnded(self):
        log.d('onPlayBackEnded')
        self.manual_stopped = False
        self.onPlayBackStopped()
        xbmc.Player.onPlayBackEnded(self)

    def onPlayBackStarted(self):    
        try:
            log.d('onPlayBackStarted: {0} {1} {2}'.format(xbmcgui.getCurrentWindowId(), self.amalker, self.getPlayingFile()))
        except Exception as e:
            log.e('onPlayBackStarted: {0}'.format(e))
        
        if not self.amalker:
            self.parent.player.show()
        elif self.amalker:
            log.d('SHOW ADS Window')
            self.parent.amalkerWnd.show()
            log.d('END SHOW ADS Window')
        self.manual_stopped = True
        self.parent.hide_main_window(0)
        xbmc.Player.onPlayBackStarted(self)
        
    def sockConnect(self):        
        self.sock.connect((self.server_ip, self.aceport))
        self.sock.setblocking(0)
        self.sock.settimeout(10)
                
    def startEngine(self):
        def getAceEngine_exe():
            log.d('Считываем путь к ace_engine.exe')      
            import _winreg              
            t = None
            try:
                t = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, 'Software\\ACEStream')
                return _winreg.QueryValueEx(t , 'EnginePath')[0]           
                
            except Exception, e:
                log.e('Error Opening acestream.port %s' % e)
                return ''
            finally:
                if t:    
                    _winreg.CloseKey(t)
        
        def getWinPort():
            log.d('Считываем порт')
            for i in range(15):
                if os.path.exists(self.port_file):                    
                    with open(self.port_file, 'r') as gf:
                        return int(gf.read())
                else:
                    if self.parent: 
                        self.parent.showStatus("Запуск AceEngine ({0})".format(i))                                
                    xbmc.sleep(995)
    
            return 0
    
        import subprocess
        acestream_params = ["--live-cache-type", "memory"]

        if sys.platform.startswith('win') and self.server_ip == '127.0.0.1':
            try:                
                log.d('try to start AceEngine for windows') 
                self.ace_engine = getAceEngine_exe()
                log.d("AceEngine path: {0}".format(self.ace_engine.encode('utf-8')))     
                self.port_file = os.path.join(os.path.dirname(self.ace_engine), 'acestream.port')
                
                if self.port_file != '' and os.path.exists(self.port_file):
                    os.remove(self.port_file)
                
                log.d('Пытаюсь открыть %s' % self.port_file.encode('utf-8'))
                if not os.path.exists(self.port_file):
                    if self.parent: 
                        self.parent.showStatus("Запуск AceEngine")
        
                    p = subprocess.Popen([self.ace_engine] + acestream_params)
                    log.d('pid = {0}'.format(p.pid))
                    
                    self.aceport = getWinPort()
                    if self.aceport > 0:
                        defines.ADDON.setSetting('port', str(self.aceport))
                    else:
                        return
                        
                                            
            except Exception, e:
                log.f('start AceEngine: %s' % e)
                return
        else:  
            log.d('try to start AceEngine for linux')  
            acestream_params += ["--client-console"]            
            try:
                if self.parent: 
                    self.parent.showStatus("Запуск acestreamengine")
                try:                    
                    p = subprocess.Popen(["acestreamengine"] + acestream_params)
                    log.d('pid = {0}'.format(p.pid))
                except:
                    log.d('try to start AceEngine for Android')
                    xbmc.executebuiltin('XBMC.StartAndroidActivity("org.acestream.engine")')
                    xbmc.sleep(100) 
                    xbmc.executebuiltin('XBMC.StartAndroidActivity("org.xbmc.kodi")')               
            except Exception as e:
                log.f('Cannot start AceEngine')
                return
        return True
    
    def get_key(self, key):
        try:
            import hashlib
            pkey = 'n51LvQoTlJzNGaFxseRK-uvnvX-sD4Vm5Axwmc4UcoD-jruxmKsuJaH0eVgE'
            sha1 = hashlib.sha1()
            sha1.update(key + pkey)
            key = sha1.hexdigest()
            pk = pkey.split('-')[0]
            return "%s-%s" % (pk, key)
        except:
            return defines.GET("http://api.torrent-tv.ru/xbmc_get_key.php?key=" + key)
        
    def connectToTS(self):
        try:
            log.d('Подключение к AceEngine %s %s ' % (self.server_ip, self.aceport))
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sockConnect()
        except Exception, e:
            if self.startEngine():
                for i in range(15):
                    try:
                        log.d("Попытка подлючения")
                        if self.parent: 
                            self.parent.showStatus("Подключение к AceEngine ({0})".format(i))
                        self.sockConnect()                            
                        break
                    except Exception, e:
                        log.e("Подключение не удалось {0}".format(e))
                        xbmc.sleep(995)
                        continue
                else:
                    msg = 'Ошибка подключения к AceEngine: {0}'.format(e)
                    log.f(msg)
                    self.parent.showStatus('Ошибка подключения к AceEngine!')
                    raise Exception(msg)  
            else:
                msg = "Не удалось запустить AceEngine!"
                self.parent.showStatus(msg)
                raise Exception(msg)
            
                
            
        if self.parent: 
            self.parent.hideStatus()

        log.d('Все ок')
        # Общаемся
        try:
            self.sendCommand('HELLOBG version=4')
            self.Wait(TSMessage.HELLOTS)
            msg = self.thr.getTSMessage()
            if msg.getType() == TSMessage.HELLOTS and not msg.getParams().has_key('key'):
                raise IOError('Incorrect msg from AceEngine')
            
            self.thr.msg = TSMessage()
            log.d('Send READY')
            self.sendCommand('READY key=' + self.get_key(msg.getParams()['key']))
            self.Wait(TSMessage.AUTH)
            msg = self.thr.getTSMessage()
            if msg.getType() == TSMessage.AUTH:
                if msg.getParams() == '0':
                    raise IOError('Пользователь не зарегистрирован')
            else:
                raise IOError('Incorrect msg from AceEngine')
            
        except IOError as io:
            self.last_error = str(io)
            if self.parent: 
                self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
            #self.end()
            return

        log.d('End Init AceEngine')
        if self.parent: 
            self.parent.hideStatus()
        
        
    def sendCommand(self, cmd):
        try:
            if not (self.thr and self.thr.active): 
                if cmd not in ("STOP", "SHUTDOWN"): 
                    self.createThread()
                else:
                    return
                
            log.d('Send command %s' % cmd)
            self.sock.send(cmd + '\r\n')
            self.trys = 0
        except Exception, e:
            log.w('sendCommand Error: {0}'.format(e))
            try:
                self.trys += 1
                if self.trys >= 3:
                    raise Exception("Can't sendCommand: {0}".format(cmd))
                if cmd not in ("STOP", "SHUTDOWN"):
                    self.connectToTS()                
                    self.sendCommand(cmd)
            except Exception, e:
                log.e('ERROR Send command: %s' % e)
                self.end()
                #self.parent.close()                 
                raise   
            
    def isCancel(self):
        return defines.closeRequested.isSet() or xbmc.abortRequested   
                
    
    def Wait(self, msg):
        log.d('wait message: {0}'.format(msg))
        a = 0
        try:
            while self.thr.getTSMessage().getType() != msg and not self.thr.error and not self.isCancel():
                xbmc.sleep(DEFAULT_TIMEOUT)
                if not self.stream: 
                    xbmc.sleep(DEFAULT_TIMEOUT)
                a += 1
                if a >= 249:
                    log.w('AceEngine is freeze')
                    if self.parent: 
                        self.parent.showStatus("Ошибка ожидания. Операция прервана")
                    raise Exception('AceEngine is freeze')
        except:
            self.stop()
    
    def createThread(self):
        self.thr = SockThread(self.sock)
        self.thr.state_method = self.showState
        self.thr.owner = self
        self.thr.start()
        
    def load_torrent(self, torrent, mode):
        log.d("Load Torrent: {0}, mode: {1}".format(torrent, mode))
        cmdparam = ''
        self.mode = mode
        if mode != TSengine.MODE_PID:
            cmdparam = ' 0 0 0'
        self.quid = str(random.randint(0, 0x7fffffff))
        self.torrent = torrent
        comm = 'LOADASYNC ' + self.quid + ' ' + mode + ' ' + torrent + cmdparam
        if self.parent: 
            self.parent.showStatus("Загрузка торрента")
        self.stop()
        
        self.sendCommand(comm)
        self.Wait(TSMessage.LOADRESP)
        msg = self.thr.getTSMessage()
        log.d('load_torrent - %s' % msg.getType())
        if msg.getType() == TSMessage.LOADRESP:
            try:
                log.d('Compile file list')
                jsonfile = msg.getParams()['json']
                if not jsonfile.has_key('files'):
                    self.parent.showStatus(jsonfile['message'])
                    self.last_error = Exception(jsonfile['message'])
                    log.e('Compile file list %s' % self.last_error)
                    return
                self.count = len(jsonfile['files'])
                self.files = {}
                for f in jsonfile['files']:
                    self.files[f[1]] = urllib.unquote_plus(urllib.quote(f[0]))
                log.d('End Compile file list')
            except Exception, e:
                log.e(e)
                self.last_error = e
                self.end()
        else:
            self.last_error = 'Incorrect msg from AceEngine'
            if self.parent: 
                self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
            log.f('Incorrect msg from AceEngine %s' % msg.getType())
            self.stop()
            return

        if self.parent: self.parent.hideStatus()

    def showState(self, state):
        if state.getType() == TSMessage.STATUS and self.parent:
            _params = state.getParams()
            if _params.has_key('main'):
                _descr = _params['main'].split(';')
                if _descr[0] == 'prebuf':
                    log.d('showState: Пытаюсь показать состояние')
                    self.parent.showStatus('Пребуферизация %s' % _descr[1])
                elif _descr[0] == 'check':
                    log.d('showState: Проверка %s' % _descr[1])
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
        log.d("Запуск торрента")
        self.stop()
        xbmc.sleep(4)
        self.sendCommand(comm)
        if self.parent: 
            self.parent.showStatus("Запуск торрента")
        self.Wait(TSMessage.START)
        msg = self.thr.getTSMessage()
        if msg.getType() == TSMessage.START:
            try:
                _params = msg.getParams()
                if not _params.has_key('url'):
                    if self.parent: 
                        self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
                    raise Exception('Incorrect msg from AceEngine %s' % msg.getType())

                self.amalker = _params.has_key('ad') and not _params.has_key('interruptable')
                self.link = _params['url'].replace('127.0.0.1', self.server_ip).replace('6878', self.webport)
                log.d('Преобразование ссылки: %s' % self.link)
                self.title = title
                self.icon = icon
                self.playing = True
                
                self.thr.msg = TSMessage()
                if self.amalker:
                    self.parent.showStatus('Рекламный ролик')
                #    self.parent.player.doModal()
                # else:
                #    self.parent.amalker.show()
                log.d('Первый запуск. Окно = %s. Реклама = %s' % (xbmcgui.getCurrentWindowId(), self.amalker))
                self.icon = icon
                self.thumb = thumb
                lit = xbmcgui.ListItem(title, iconImage=icon, thumbnailImage=thumb)
                self.play(self.link, lit, windowed=True)
                self.playing = True
                self.onPlayBackStarted()
                self.loop()
            except Exception, e:
                log.e(e)
                self.last_error = e
                if self.parent: 
                    self.parent.showStatus("Ошибка. Операция прервана")
                self.stop()
        else:
            self.last_error = 'Incorrect msg from AceEngine %s' % msg.getType()
            log.e(self.last_error)
            if self.parent: 
                self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
            self.stop()

    def loop(self):
        while self.isPlaying() and not self.isCancel():
            if self.isPlaying() and self.amalker and (self.getTotalTime() - self.getTime()) < 0.5:
                self.parent.amalkerWnd.close()
                break
            try:
                if xbmc.abortRequested:
                    log.d("XBMC Shutdown")
                    break
                xbmc.sleep(250)

            except Exception as e:
                log.e('ERROR SLEEPING: {0}'.format(e))
                self.end()
                #self.parent.close()
                raise
            

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
                    self.loop()
                except Exception, e:
                    log.e(e)
                    self.last_error = e
                    if self.parent: 
                        self.parent.showStatus("Ошибка. Операция прервана")
                    self.stop()
            else:
                self.last_error = 'Incorrect msg from AceEngine %s' % msg.getType()
                if self.parent: 
                    self.parent.showStatus("Неверный ответ от AceEngine. Операция прервана")
                log.e(self.last_error)
                self.stop()

    def end(self):
        self.playing = False
        self.link = None
        self.sendCommand('STOP')
        self.sendCommand('SHUTDOWN')
        self.last_error = None
        if self.thr:
            self.thr.active = False
            self.thr = None
        self.sock.close()  
        xbmc.Player.stop(self)      

    def stop(self):
        log.d('stop player method')        
        self.playing = False
        self.link = None
        self.sendCommand('STOP')        
        if self.thr:
            self.thr.active = False
            #self.thr.join()
            self.thr = None
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
        self.daemon = False
        self.sock = _sock
        self.buffer = 65020
        self.isRecv = False
        self.lastRecv = ''
        self.lstCmd = ''
        self.active = True
        self.error = None
        self.msg = TSMessage()
        self.state_method = None
        self.owner = None
        

    def run(self):
        def isCancel():
            return not self.active or self.error or self.owner.isCancel()
        
        log.d('Start SockThread')
        while not isCancel():
            try:
                xbmc.sleep(32)
                self.lastRecv += self.sock.recv(self.buffer)
                if self.lastRecv.find('\r\n') > -1:
                    cmds = self.lastRecv.split('\r\n')
                    for cmd in cmds:                        
                        if len(cmd.replace(' ', '')) > 0 and not isCancel():
                            #log.d('RUN Получена комманда = ' + cmd)
                            self._constructMsg(cmd)
                    self.lastRecv = ''
            except Exception, e:
                self.isRecv = True
                self.active = False
                self.error = e
                log.e('RECV THREADING %s' % e)
                _msg = TSMessage()
                _msg.type = TSMessage.ERROR
                _msg.params = 'Ошибка соединения с AceEngine'
                self.state_method(_msg)
                # self.owner.end()
                # self.owner.connectToTS()
                # self.owner.parent.close()
        log.d('Close from thread')
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
        elif _msg == TSMessage.PAUSE:
            msg = TSMessage()
            msg.setType(TSMessage.PAUSE)
            log.d("GET PAUSE")
            self.state_method(msg)
        elif _msg == TSMessage.RESUME:
            msg = TSMessage()
            msg.setType(TSMessage.RESUME)
            log.d("GET RESUME")
            self.state_method(msg)


    def getTSMessage(self):
        res = copy.deepcopy(self.msg)
        return res

    def end(self):
        self.active = False

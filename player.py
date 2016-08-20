  # -*- coding: utf-8 -*-
# Copyright (c) 2014 Torrent-TV.RU
# Writer (c) 2014, Welicobratov K.A., E-mail: 07pov23@gmail.com
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

import xbmcgui
import threading
import xbmc
import time, datetime
import defines
import json
import re
from ext.table import Channels as ExtChannels

from ts import TSengine as tsengine
# defines
CANCEL_DIALOG = (9, 10, 11, 92, 216, 247, 257, 275, 61467, 61448,)

log = defines.Logger('MyPlayer')

class MyPlayer(xbmcgui.WindowXML):
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

    def __init__(self, *args, **kwargs):
        log.d('__init__')
        self.TSPlayer = None
        self.parent = None
        self.li = None
        self.visible = False        
        self.focusId = MyPlayer.CONTROL_WINDOW_ID
        
        self.select_timer = None
        self.hide_control_timer = None
        self.hide_swinfo_timer = None
        
        self.channel_number = 0
        self.channel_number_str = ''
        self.chinfo = None
        self.swinfo = None
        self.control_window = None
        

    def onInit(self):
        log.d('onInit')
        if not self.li:
            return      
        self.progress = self.getControl(MyPlayer.CONTROL_PROGRESS_ID)  
        cicon = self.getControl(MyPlayer.CONTROL_ICON_ID)
        cicon.setImage(self.li.getProperty('icon'))
        self.control_window = self.getControl(MyPlayer.CONTROL_WINDOW_ID)
        self.chinfo = self.getControl(MyPlayer.CH_NAME_ID)
        self.chinfo.setLabel(self.li.getLabel())
        self.swinfo = self.getControl(MyPlayer.DLG_SWITCH_ID)
        self.swinfo.setVisible(False)
        if not self.parent:
            return
    
        if not self.select_timer:
            self.init_channel_number()
        
        log.d("channel_number = %i" % self.channel_number)
        log.d("selitem_id = %i" % self.parent.selitem_id)    
        
        self.UpdateEpg(self.li)
        
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
            
        if self.hide_control_timer:
            self.hide_control_timer.cancel()
            self.hide_control_timer = None
        self.hide_control_timer = threading.Timer(timeout, hide)
        self.hide_control_timer.name = 'hide_control_window'
        self.hide_control_timer.daemon = False
        self.hide_control_timer.start()
        
        
    def UpdateEpg(self, li):
        try:
            log.d('UpdateEpg')
            if not li:
                raise ValueError('param "li" is not set')
            cicon = self.getControl(MyPlayer.CONTROL_ICON_ID)
            cicon.setImage(li.getProperty('icon'))
            epg_id = li.getProperty('epg_cdn_id')
            
            if self.parent.epg.get(epg_id):
                self.showEpg(epg_id)
            else:
                self.parent.getEpg(epg_id, callback=self.showEpg)
                      
        except Exception as e:
            log.w('UpdateEpg error: {0}'.format(e))
            
        
    def showEpg(self, epg_id):        
        try:
            ctime = datetime.datetime.now()
            dt = (ctime - datetime.datetime.utcnow()) - datetime.timedelta(hours=3)            
            curepg = self.parent.getCurEpg(epg_id)
            
            for i, ep in enumerate(curepg):
                try:
                    ce = self.getControl(MyPlayer.CONTROL_FIRST_EPG_ID + i)
                    bt = datetime.datetime.fromtimestamp(float(ep['btime']))
                    et = datetime.datetime.fromtimestamp(float(ep['etime']))
                    ce.setLabel(u"{0} - {1} {2}".format(bt.strftime("%H:%M"), et.strftime("%H:%M"), ep['name'].replace('&quot;', '"')))
                    if i == 0:
                        self.progress.setPercent((ctime - bt).seconds * 100 / (et - bt).seconds)
                except:
                    break
                
            return True
        
        except Exception as e:
            log.e('showEpg error {}'.format(e))
            
        for i in range(99):
            try:
                ce = self.getControl(MyPlayer.CONTROL_FIRST_EPG_ID + i)                
                if i == 0:
                    ce.setLabel('Нет программы')
                else:
                    ce.setLabel('')
            except:
                break
        self.progress.setPercent(1)
        
            
    def Stop(self):
        log('AutoStop')
        # xbmc.executebuiltin('PlayerControl(Stop)')
        if self.TSPlayer:
            self.TSPlayer.manual_stopped = False
            self.TSPlayer.stop()
        
            
    def Show(self):
        if self.TSPlayer:
            if not self.TSPlayer.amalker:
                self.show()
            else:
                log.d('SHOW ADS Window')
                self.parent.amalkerWnd.show()
                log.d('END SHOW ADS Window')
                

    def Start(self, li):
        def get_channel_from_ext():
            def get_src(url):
                try:
                    if url.find('acestream://') > -1:
                        return url.replace('acestream://', '')
                    if url.rfind('.acelive') > -1:
                        return url
                    http = defines.GET(url, trys=2)
                    m = re.search('(loadPlayer|loadTorrent)\("(?P<src>[\w/_:.]+)"', http)
                    return m.group('src')            
                except Exception as e:
                    log.w('Start->get_from_ext->get_src error: {0}'.format(e))  
            
            for tch in ExtChannels.itervalues():
                chli = tch.find_by_id(li.getProperty("id"))
                if not chli:
                    chli = tch.find_by_title(li.getProperty('name'))
                if chli:
                    src = get_src(chli.get('url'))
                    if src:                             
                        jdata["success"] = 1
                        if src.rfind('.acelive') > -1:
                            jdata["type"] = 'TORRENT'
                        else:                                
                            jdata["type"] = 'PID'
                            
                        jdata["source"] = src
                        return jdata
             
        def get_channel_from_api():           
            data = defines.GET("http://{0}/v3/translation_stream.php?session={1}&channel_id={2}&typeresult=json".format(defines.API_MIRROR, self.parent.session, li.getProperty("id")))
            try:
                jdata = json.loads(data)
                return jdata
            except Exception as e:
                log.w('Start->get_from_api error: {0}'.format(e))
                
        def get_record_from_api():
            data = defines.GET("http://{0}/v3/arc_stream.php?session={1}&record_id={2}&typeresult=json".format(defines.API_MIRROR, self.parent.session, li.getProperty("id")))
            try:
                jdata = json.loads(data)
                return jdata
            except Exception as e:
                log.w('Start->get_record_from_api error: {0}'.format(e))
                
        log("Start play")       

        self.li = li
        self.channel_number = self.parent.selitem_id
        
        self.parent.showStatus("Получение ссылки...")
        
        if (li.getProperty("type") == "channel"):
            jdata = get_channel_from_api()
                        
            if not jdata or not jdata.get("success") or jdata.get("success") == 0 or not jdata.get("source"):
                jdata = get_channel_from_ext()
            
        elif (li.getProperty("type") == "record"):
            jdata = get_record_from_api()
        else:
            msg = "Неизвестный тип контента"
            self.parent.showStatus(msg)
            raise Exception(msg)
            
        if not jdata or not jdata.get("success") or jdata.get("success") == 0 or not jdata.get("source"):
            msg = "Канал временно не доступен"
            self.parent.showStatus(msg)
            raise Exception(msg)

        url = jdata["source"]
        mode = jdata["type"].upper().replace("CONTENTID", "PID")
        self.parent.hideStatus()
        
        log.d('Play torrent')
        if not self.TSPlayer:
            log.d('InitTS')
            self.TSPlayer = tsengine(parent=self.parent)
        self.TSPlayer.play_url_ind(0, li.getLabel(), li.getProperty('icon'), li.getProperty('icon'), torrent=url, mode=mode)
        log.d('End playing')
    
                
    def run_selected_channel(self, timeout=0):        
        def run():
            self.channel_number = defines.tryStringToInt(self.channel_number_str)        
            log.d('CHANNEL NUMBER IS: %i' % self.channel_number)              
            if 0 < self.channel_number < self.parent.list.size() and self.parent.selitem_id != self.channel_number:            
                self.parent.selitem_id = self.channel_number
                self.Stop()           
            else:       
                self.swinfo.setVisible(False)     
            self.channel_number = self.parent.selitem_id  
            self.chinfo.setLabel(self.parent.list.getListItem(self.parent.selitem_id).getLabel()) 
            self.channel_number_str = ''
        
        if self.select_timer: 
            self.select_timer.cancel() 
            self.select_timer = None
        self.select_timer = threading.Timer(timeout, run)
        self.select_timer.name = 'run_selected_channel'
        self.select_timer.daemon = False
        self.select_timer.start()    
        
    
    def inc_channel_number(self):
        self.channel_number += 1
        if self.channel_number >= self.parent.list.size():
            self.channel_number = 1
    
    
    def dec_channel_number(self):
        self.channel_number -= 1
        if self.channel_number <= 0:
            self.channel_number = self.parent.list.size() - 1
            
            
    def onAction(self, action):
        # log.d('Action {0} | ButtonCode {1}'.format(action.getId(), action.getButtonCode()))
        if action in CANCEL_DIALOG or action.getId() == MyPlayer.ACTION_RBC:
            log.d('Close player %s %s' % (action.getId(), action.getButtonCode()))
            self.close()
        elif action.getId() in (3, 4, 5, 6): 
            ############### IF ARROW UP AND DOWN PRESSED - SWITCH CHANNEL ###############
            if action.getId() in (3, 5):
                self.inc_channel_number()
            else:
                self.dec_channel_number()
                
            self.channel_number_str = str(self.channel_number)
            self.swinfo.setVisible(True) 
            li = self.parent.list.getListItem(self.channel_number)                            
            self.chinfo.setLabel(li.getLabel())
            self.UpdateEpg(li)
            
            self.run_selected_channel(timeout=5)
            
        elif action.getId() in MyPlayer.DIGIT_BUTTONS:
            ############# IF PRESSED DIGIT KEYS - SWITCH CHANNEL #######################
            digit_pressed = action.getId() - 58 
            if digit_pressed < self.parent.list.size():
                                
                self.channel_number_str += str(digit_pressed)                 
                self.channel_number = defines.tryStringToInt(self.channel_number_str) 
                if not 0 < self.channel_number < self.parent.list.size():   
                    self.channel_number_str = str(digit_pressed) 
                    self.channel_number = defines.tryStringToInt(self.channel_number_str)                   
                
                li = self.parent.list.getListItem(self.channel_number)                            
                self.chinfo.setLabel(li.getLabel())
                self.swinfo.setVisible(True)
                self.UpdateEpg(li)
                
                self.run_selected_channel(timeout=5) 
        elif action.getId() == 0 and action.getButtonCode() == 61530:
            xbmc.executebuiltin('Action(FullScreen)')
            xbmc.sleep(4000)
            xbmc.executebuiltin('Action(Back)')
        else:
            self.UpdateEpg(self.li)

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
        if self.hide_control_timer:
            self.hide_control_timer.cancel()
        if self.hide_swinfo_timer:
            self.hide_swinfo_timer.cancel()
        if self.select_timer:
            self.select_timer.cancel()
        xbmcgui.WindowXML.close(self)
            
        

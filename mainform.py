# -*- coding: utf-8 -*-
# Copyright (c) 2013 Torrent-TV.RU
# Writer (c) 2013, Welicobratov K.A., E-mail: 07pov23@gmail.com
# Edited (c) 2015, Vorotilin D.V., E-mail: dvor85@mail.ru

# imports
import defines
import xbmcgui
import xbmc

import time
import datetime
import threading
import BeautifulSoup

from player import MyPlayer
from adswnd import AdsForm
from menu import MenuForm
from infoform import InfoForm
from dateform import DateForm
from tchannels import TChannels
import uuid
import os
import favdb
import json
import re
from UserDict import UserDict

log = defines.Logger('MainForm')


class ChannelGroups(UserDict):
    def __init__(self):
        self.data = {}
        
    def setGroup(self, groupname, grouptitle):
        self.data[groupname] = {"title": grouptitle, "channels": []}
        
    def delGroup(self, groupname):
        del self.data[groupname]
        
    def getGroups(self):
        return self.data.keys()
    
    def setChannels(self, groupname, channels):
        self.data[groupname]["channels"] = channels
        
    def addChannel(self, groupname, channel):
        self.data[groupname]["channels"].append(channel)
        
    def delChannel(self, groupname, chid):
        for li in self.data[groupname]["channels"]:
            if li.getProperty('id') == chid:
                self.data[groupname]["channels"].remove(li)
                
    def getChannels(self, groupname):
        return self.data[groupname]["channels"]
        
    def getChannel(self, groupname, chid):
        for li in self.data[groupname]["channels"]:
            if li.getProperty('id') == chid:
                return li  

class WMainForm(xbmcgui.WindowXML):
    CANCEL_DIALOG = (9, 10, 11, 92, 216, 247, 257, 275, 61467, 61448,)
    CONTEXT_MENU_IDS = (117, 101)
    ARROW_ACTIONS = (1, 2, 3, 4)
    DIGIT_BUTTONS = range(58, 68)
    ACTION_MOUSE = 107
    BTN_CHANNELS_ID = 102
    BTN_TRANSLATIONS_ID = 103
    BTN_ARCHIVE_ID = 104
    BTN_VOD_ID = 113
    BTN_CLOSE = 101
    BTN_FULLSCREEN = 208
    IMG_SCREEN = 210
    CONTROL_LIST = 50
    PANEL_ADS = 105
    
    TXT_PROGRESS = 107
    IMG_PROGRESS = 108
    PROGRESS_BAR = 110
    
    BTN_INFO = 209
    LBL_FIRST_EPG = 300
    
    CHN_TYPE_FAVOURITE = 'Избранное'
    CHN_TYPE_ONETTVNET = '1ttv.net'
    CHN_TYPE_TRANSLATION = 'Трансляции'
    CHN_TYPE_MODERATION = 'На модерации'
    API_ERROR_INCORRECT = 'incorrect'
    API_ERROR_NOCONNECT = 'noconnect'
    API_ERROR_ALREADY = 'already'
    API_ERROR_NOPARAM = 'noparam'
    API_ERROR_NOFAVOURITE = 'nofavourite'    


    def __init__(self, *args, **kwargs):
        log.d('__init__')
        self.translation = []
        self.channel_groups = ChannelGroups()
        self.seltab = 0
        self.epg = {}
        self.archive = []
        self.selitem = '0'
        self.img_progress = None
        self.txt_progress = None
        self.list = None
        self.player = MyPlayer("player.xml", defines.SKIN_PATH, defines.ADDON.getSetting('skin'))
        self.player.parent = self
        self.amalkerWnd = AdsForm("adsdialog.xml", defines.SKIN_PATH, defines.ADDON.getSetting('skin'))
        self.load_selitem_info()            
        self.playditem = -1
        self.user = None
        self.infoform = None
        self.init = True
        self.session = None
        self.cookie = None
        self.onettvnet = None
        self.channel_number_str = ''
        self.select_timer = None
        self.hide_window_timer = None
        self.get_epg_timer = None
        self.show_screen_timer = None
        
        self.initTTV()
        
    def initTTV(self):
        data = defines.GET('http://{0}/v3/version.php?application=xbmc&version={1}'.format(defines.API_MIRROR, defines.TTV_VERSION))
        try:
            jdata = json.loads(data)
            if jdata['success'] == 0:                
                raise Exception(jdata['error'])
#             raise Exception('Test')    
        except Exception as e:
            log.e('onInit error: {0}'.format(e))
            msg = 'Ошибка Torrent-TV.RU'
            defines.showNotification(msg, xbmcgui.NOTIFICATION_ERROR)
            self.close()
            return
        if jdata['support'] == 0:
            self.showDialog("Текущая версия приложения (%s) не поддерживается. Последняя версия %s " % (defines.TTV_VERSION, jdata['last_version'].encode('utf-8')))
            self.close()
            return
        
        self.showStatus("Авторизация")
        guid = defines.ADDON.getSetting("uuid")
        if guid == '':
            guid = str(uuid.uuid1())
            defines.ADDON.setSetting("uuid", guid)
        guid = guid.replace('-', '')
        data = defines.GET('http://{0}/v3/auth.php?username={1}&password={2}&typeresult=json&application=xbmc&guid={3}'.format(defines.API_MIRROR, defines.ADDON.getSetting('login'), defines.ADDON.getSetting('password'), guid))
        try:
            jdata = json.loads(data)
            if jdata['success'] == 0:                
                raise Exception(jdata['error'])
        except Exception as e:
            log.e('onInit error: {0}'.format(e))
            msg = 'Ошибка Torrent-TV.RU'
            defines.showNotification(msg, xbmcgui.NOTIFICATION_ERROR)
            self.close()             
            return
        
        self.user = {"login" : defines.ADDON.getSetting('login'), "balance" : jdata["balance"], "vip":jdata["balance"] > 1}
        
        self.session = jdata['session']
#         self.cookie = defines.AUTH()
#         self.cookie = ["PHPSESSID=710f1ae31db941b19ff75ac3a9d44dd0"]
        
    
    def onInit(self):
        self.img_progress = self.getControl(WMainForm.IMG_PROGRESS)
        self.txt_progress = self.getControl(WMainForm.TXT_PROGRESS)
        self.progress = self.getControl(WMainForm.PROGRESS_BAR)
        
#         self.initTTV()
        if not self.channel_groups:            
            self.updateList()
        else:
            self.loadList()    
        self.hide_main_window(timeout=10)
        
        
    def showDialog(self, msg):
        from okdialog import OkDialog
        dialog = OkDialog("okdialog.xml", defines.SKIN_PATH, defines.ADDON.getSetting('skin'))
        dialog.setText(msg)
        dialog.doModal()
        
    
    def onFocus(self, ControlID):
        if ControlID == WMainForm.CONTROL_LIST:
            if not self.list:
                return
            selItem = self.list.getSelectedItem()
            if selItem:
                if selItem.getLabel2() == self.selitem or selItem.getLabel() == '..':
                    return
                self.selitem = selItem.getLabel2()
                self.selitem_id = self.list.getSelectedPosition()
                log.d('Selected %s' % self.selitem_id)
                epg_id = selItem.getProperty('epg_cdn_id')
                img = self.getControl(WMainForm.IMG_SCREEN)
                img.setImage("")
                
                if epg_id == '0':
                    self.showSimpleEpg()
                elif self.epg.has_key(epg_id):
                    self.showSimpleEpg(epg_id)
                else:
                    self.getEpg(epg_id, timeout=1)
                
                self.showScreen(selItem.getProperty('id'), timeout=1)
                img = self.getControl(1111)
                img.setImage(selItem.getProperty('icon'))
        
        
    def load_selitem_info(self):        
        self.cur_category = defines.ADDON.getSetting('cur_category')
        self.selitem_id = defines.ADDON.getSetting('cur_channel')
        if self.cur_category == '':
            self.cur_category = WMainForm.CHN_TYPE_FAVOURITE
        
        if self.selitem_id == '':
            self.selitem_id = -1 
        else:
            self.selitem_id = defines.tryStringToInt(self.selitem_id)          


    def getChannels(self, *args):
        param = args[0]
        log.d('getChannels {0}'.format(param))        
        try:
            if param == WMainForm.CHN_TYPE_ONETTVNET:    
                
                from ext.onettvnet import Channels 
                jdata = {'channels': TChannels(Channels).get(), 'categories':[], 'success': 1} 
            else:
                data = defines.GET('http://{0}/v3/translation_list.php?session={1}&type={2}&typeresult=json'.format(defines.API_MIRROR, self.session, param), cookie=['PHPSESSID=%s' % self.session], trys=10)
                jdata = json.loads(data)
            if jdata['success'] == 0:
                raise Exception(jdata['error'])            
        except Exception as e:
            log.e('getChannels error: {0}'.format(e))
            msg = "Ошибка Torrent-TV.RU"
            self.showStatus(msg)
            return
            
        

        for cat in jdata["categories"]:
            if not self.channel_groups.has_key('%s' % cat["id"]):
                self.channel_groups.setGroup('%s' % cat["id"], cat["name"])
        
        if param == 'favourite':  
            fdb = favdb.LocalFDB()          
            if len(jdata['channels']) > 0 and self.user["vip"] and self.init:
                fdb.save(jdata['channels'])
            elif not self.user["vip"]:
                jdata['channels'] = fdb.get()
                
        if jdata['channels']:
            for ch in jdata['channels']:
                if not ch["name"]:
                    continue
                if not ch['logo']:
                    ch['logo'] = ''
                else:
                    ch['logo'] = 'http://{0}/uploads/{1}'.format(defines.SITE_MIRROR, ch['logo'])    
                            
                li = xbmcgui.ListItem(ch["name"], '%s' % ch['id'], ch['logo'], ch['logo'])
                li.setProperty('name', ch["name"])
                li.setProperty('epg_cdn_id', '%s' % ch['epg_id'])
                li.setProperty('icon', ch['logo'])
                li.setProperty("type", "channel")
                li.setProperty("id", '%s' % ch["id"])
                li.setProperty("access_translation", '%s' % ch["access_translation"])
                li.setProperty("access_user", '%s' % ch["access_user"])
                if ch.has_key('url'):
                    li.setProperty("url", ch['url'])
                
                if param == 'channel':
                    li.setProperty('commands', "%s" % (MenuForm.CMD_ADD_FAVOURITE))
                    self.channel_groups.addChannel('%s' % ch['group'], li)
                    
                elif param == WMainForm.CHN_TYPE_ONETTVNET:
                    li.setProperty('commands', "%s" % (MenuForm.CMD_ADD_FAVOURITE))
                    self.channel_groups.addChannel(WMainForm.CHN_TYPE_ONETTVNET, li)
                    
                elif param == 'moderation':
                    li.setProperty('commands', "%s" % (MenuForm.CMD_ADD_FAVOURITE))
                    self.channel_groups.addChannel(WMainForm.CHN_TYPE_MODERATION, li)
                            
                elif param == 'translation':
                    li.setProperty('commands', "%s" % (MenuForm.CMD_ADD_FAVOURITE))
                    self.translation.append(li)
                    
                elif param == 'favourite':
                    li.setProperty('commands', "%s,%s,%s,%s" % (MenuForm.CMD_MOVE_FAVOURITE, MenuForm.CMD_DEL_FAVOURITE, MenuForm.CMD_DOWN_FAVOURITE, MenuForm.CMD_UP_FAVOURITE))
                    self.channel_groups.addChannel(WMainForm.CHN_TYPE_FAVOURITE, li)
                
                    
    def getArcChannels(self, *args):
        log.d('getArcChannels')
        try:
            data = defines.GET('http://{0}/v3/arc_list.php?session={1}&typeresult=json'.format(defines.API_MIRROR, self.session), cookie=['PHPSESSID=%s' % self.session], trys=10)
            jdata = json.loads(data)
            if jdata['success'] == 0:
                raise Exception(jdata['error'])
        except Exception as e:
            log.e('getArcChannels error: {0}'.format(e))
            msg = "Ошибка Torrent-TV.RU"
            self.showStatus(msg)
            return
        
        self.archive = []
        
        for ch in jdata['channels']:
            chname = "%i. %s" % ((len(self.archive) + 1), ch["name"])
            if not ch["id"]:
                continue
            if not ch["logo"]:
                ch["logo"] = ""
            else:
                ch["logo"] = "http://{0}/uploads/{1}".format(defines.SITE_MIRROR, ch["logo"])
            li = xbmcgui.ListItem(chname, '%s' % ch["id"], ch["logo"], ch["logo"])
            li.setProperty("epg_cdn_id", '%s' % ch["epg_id"])
            li.setProperty("icon", ch["logo"])
            li.setProperty("type", "archive")
            self.archive.append(li)


    def getEpg(self, epg_id, timeout=0, blocking=False):
        def get(*args):
            try:
                log.d('getEpg')
                self.showStatus('Загрузка программы')
                param = args[0]
                if param[0] != '#':
                    data = defines.GET('http://{0}/v3/translation_epg.php?session={1}&epg_id={2}&typeresult=json'.format(defines.API_MIRROR, self.session, param), cookie=['PHPSESSID=%s' % self.session], trys=10)
                    jdata = json.loads(data)
                    if jdata['success'] == 0:
                        self.epg[param] = []
                        self.showSimpleEpg(param)
                    else:
                        self.epg[param] = jdata['data']                    
                else:
                    self.epg[param] = self.get_epg_for_chid(param)
                    
                selitem = self.list.getSelectedItem()
                if selitem and selitem.getProperty('epg_cdn_id') == param:
                    self.showSimpleEpg(param)
                    
                self.hideStatus()
                   
            except Exception as e:
                log.e('getEpg error: {0}'.format(e))
            

        if self.get_epg_timer:
            self.get_epg_timer.cancel()
            self.get_epg_timer = None
         
        self.get_epg_timer = threading.Timer(timeout, get, [epg_id])
        self.get_epg_timer.name = 'getEpg'
        self.get_epg_timer.daemon = False
        self.get_epg_timer.start()
        if blocking:
            self.get_epg_timer.join(10)
        
        
    def get_epg_for_chid(self, chepg):        
        try:
            chid = chepg[1:]
            http = defines.GET(self.channel_groups.getChannel(self.cur_category, chid).getProperty('url'), trys=1, cookie=self.cookie)
            m = re.search('var\s+epg\s*=\s*(?P<e>\[[^\]]+\])', http)
            epgtext = re.sub('(?P<k>\w+\s*):\s*(?P<v>.+[,}])', '"\g<k>":\g<v>', m.group('e'))
            epg = json.loads(epgtext)   
            return epg 
        except Exception as e:
            log.e('get_epg_for_chid error: {0}'.format(e))
            
            
    def showScreen(self, cdn, timeout=0):
        def show(*args):
            log.d('showScreen')
            cdn = args[0]
            if defines.tryStringToInt(cdn) < 1:
                return
            
            try:
                data = defines.GET('http://{0}/v3/translation_screen.php?session={1}&channel_id={2}&typeresult=json&count=1'.format(defines.API_MIRROR, self.session, cdn), cookie=['PHPSESSID=%s' % self.session], trys=10)
                jdata = json.loads(data)
                if jdata['success'] == 0:
                    raise Exception(jdata['error'])
            except Exception as e:
                log.e('showScreen error: {0}'.format(e))
    #             msg = "Ошибка Torrent-TV.RU"
    #             self.showStatus(msg)
                return
            
            img = self.getControl(WMainForm.IMG_SCREEN)
            img.setImage("")
            log.d('showScreen: %s' % jdata['screens'][0]['filename'])
            img.setImage(jdata['screens'][0]['filename'])
        
        if self.show_screen_timer:
            self.show_screen_timer.cancel()
            self.show_screen_timer = None
         
        self.show_screen_timer = threading.Timer(timeout, show, [cdn])
        self.show_screen_timer.name = 'show_screen'
        self.show_screen_timer.daemon = False
        self.show_screen_timer.start()
    
    def checkButton(self, controlId):
        control = self.getControl(controlId)
        control.setLabel('>%s<' % control.getLabel())
        if self.seltab:
            btn = self.getControl(self.seltab)
            btn.setLabel(btn.getLabel().replace('<', '').replace('>', ''))
        self.seltab = controlId
        log.d('Focused %s %s' % (WMainForm.CONTROL_LIST, self.selitem_id))
        if (self.list) and (0 < self.selitem_id < self.list.size()):     
            self.list.selectItem(self.selitem_id)  
            if self.init:
                self.init = False             
                self.emulate_startChannel()
               
                
    def select_channel(self, sch='', timeout=0): 
        if sch != '':
            self.channel_number_str = str(sch)
        chnum = defines.tryStringToInt(self.channel_number_str)                       
        log('CHANNEL NUMBER IS: %i' % chnum)              
        if 0 < chnum < self.list.size():            
            self.selitem_id = chnum
            self.setFocus(self.list)
            self.list.selectItem(self.selitem_id)    
        if self.select_timer:
            self.select_timer.cancel()
            self.select_timer = None      
        self.select_timer = threading.Timer(timeout, lambda: setattr(self, 'channel_number_str', ''))
        self.select_timer.name = 'select_channel'
        self.select_timer.daemon = False
        self.select_timer.start()
        
        
    def hide_main_window(self, timeout=0):
        log.d('hide main window in {0} sec'.format(timeout))
        
        def isPlaying():
            return not self.IsCanceled() and self.player.TSPlayer and self.player.TSPlayer.isPlaying()
        
        def hide():
            log.d('isPlaying={0}'.format(isPlaying()))
            if isPlaying():
                log.d('hide main window')
                self.player.Show()
        
        if self.hide_window_timer:
            self.hide_window_timer.cancel()
            self.hide_window_timer = None
        
        self.hide_window_timer = threading.Timer(timeout, hide)
        self.hide_window_timer.name = 'hide_main_window'
        self.hide_window_timer.daemon = False
        self.hide_window_timer.start()
                
            
    def emulate_startChannel(self):
        self.setFocusId(WMainForm.CONTROL_LIST)
        xbmc.sleep(1000)
        self.onClick(WMainForm.CONTROL_LIST)


    def onClickChannels(self):
        log.d('onClickChannels')
        self.fillChannels()
        if self.seltab != WMainForm.BTN_CHANNELS_ID:
            self.checkButton(WMainForm.BTN_CHANNELS_ID)
            
            
    def onClickTranslations(self):
        self.fillTranslation()
        if self.seltab != WMainForm.BTN_TRANSLATIONS_ID:
            self.checkButton(WMainForm.BTN_TRANSLATIONS_ID)


    def onClickArchive(self):
        self.fillArchive()        
        if self.seltab != WMainForm.BTN_ARCHIVE_ID:
            self.checkButton(WMainForm.BTN_ARCHIVE_ID)
            
            
    def LoopPlay(self, *args):  
        while not self.IsCanceled():
            try: 
                selItem = self.list.getListItem(self.selitem_id)
                
                if selItem.getProperty("access_user") == 0:
                    access = selItem.getProperty("access_translation")
                    if access == "registred":
                        defines.showNotification("Трансляция доступна для зарегестрированных пользователей", xbmcgui.NOTIFICATION_ERROR)
                    elif access == "vip":
                        defines.showNotification("Трансляция доступна для VIP пользователей", xbmcgui.NOTIFICATION_ERROR)
                    else:
                        defines.showNotification("На данный момент трансляция не доступна", xbmcgui.NOTIFICATION_ERROR)
                    break
                     
                buf = xbmcgui.ListItem(selItem.getLabel())
                buf.setProperty('epg_cdn_id', selItem.getProperty('epg_cdn_id'))
                buf.setProperty('icon', selItem.getProperty('icon'))
                buf.setProperty("type", selItem.getProperty("type"))
                buf.setProperty("id", selItem.getProperty("id"))
                if selItem.getProperty("type") == "archive":
                    self.fillRecords(buf, datetime.datetime.today())                
                    break
                log.d(selItem.getProperty("type"))
                self.playditem = self.selitem_id
                defines.ADDON.setSetting('cur_category', self.cur_category)
                defines.ADDON.setSetting('cur_channel', str(self.selitem_id))
            
                self.player.Start(buf)
                
                if self.player.TSPlayer.manual_stopped:
                    break       
                if not self.IsCanceled():
                    xbmc.sleep(223)   
                    self.select_channel(str(self.selitem_id))  
                     
            except Exception as e:
                log.e('LoopPlay error: {0}'.format(e))
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
#         elif xbmc.getCondVisibility("Window.IsMedia"):
#             self.close()
#             log.d("Is media Window")
        elif xbmc.getCondVisibility("Window.IsVisible(12346)"):
            self.close()
            log.d("Is plugin Window")
        else:
            jrpc = json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"GUI.GetProperties","params":{"properties":["currentwindow"]},"id":1}'))
            if jrpc["result"]["currentwindow"]["id"] == 10025:
                log.d("Is video plugins window")
                self.close()
             
            
    def onClick(self, controlID):
        control = self.getControl(controlID)
        log.d('onClick %s' % controlID)
        if controlID == WMainForm.BTN_CHANNELS_ID: 
            self.onClickChannels()
            log.d("playditem = %s" % self.playditem)
            if self.playditem > -1:
                self.setFocus(self.list)
                self.list.selectItem(self.playditem)
                self.playditem = -1
               
                
        elif controlID == WMainForm.BTN_TRANSLATIONS_ID: 
            self.onClickTranslations()
            if self.playditem > -1:
                self.setFocus(self.list)
                self.list.selectItem(self.selitem_id)
                self.playditem = -1

        elif controlID == WMainForm.BTN_ARCHIVE_ID: 
            self.onClickArchive()
            
        elif controlID == 200: 
            self.setFocusId(WMainForm.CONTROL_LIST)
        elif controlID == WMainForm.CONTROL_LIST:
            selItem = control.getSelectedItem()
            
            if not selItem:
                return
            log.d("selItem is {0}".format(selItem.getLabel()))
            if selItem.getLabel() == '..':
                if self.seltab == WMainForm.BTN_CHANNELS_ID:
                    self.fillCategory()
                elif self.seltab == WMainForm.BTN_ARCHIVE_ID:
                    self.fillArchive()
                return

            if selItem.getProperty('type') == 'category':
                self.cur_category = selItem.getProperty("id")
#                 self.updateList()
                self.fillChannels()
                return

            if selItem.getProperty("type") == "rec_date":
                
                if not selItem:
                    log.d("SELITEM EMPTY")
                datefrm = DateForm("dateform.xml", defines.SKIN_PATH, defines.ADDON.getSetting('skin'))
                if datefrm == None:
                    log.w('Form "{0}" not created'.format('dateform.xml'))

                stime = time.strptime(selItem.getProperty("date"), "%Y-%m-%d")
                datefrm.date = datetime.date(stime.tm_year, stime.tm_mon, stime.tm_mday)
                # datefrm.date =datetime.fromtimestamp(time.mktime(time.strptime(selItem.getProperty("date"), "%Y-%m-%d")))
                # datefrm.date = datetime.strptime(selItem.getProperty("date"), "%Y-%m-%d")
                datefrm.doModal()
                find = False
                for li in self.archive:
                    if li.getProperty("epg_cdn_id") == selItem.getProperty("epg_cdn_id"):
                        self.fillRecords(li, datefrm.date)
                        find = True
                        return
                if not find:
                    self.fillRecords(self.archive[0], datefrm.date)
                    return
            
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
            
            self.channel_groups.setChannels(WMainForm.CHN_TYPE_FAVOURITE, [])
            fthr = defines.MyThread(self.getChannels, 'favourite')
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
    

    def showSimpleEpg(self, epg_id=None):
        try:
            ctime = datetime.datetime.now()
            dt = (ctime - datetime.datetime.utcnow()) - datetime.timedelta(hours=3)
            
            curepg = []
            for x in self.epg[epg_id]:                
                bt = datetime.datetime.fromtimestamp(float(x['btime']))
                et = datetime.datetime.fromtimestamp(float(x['etime']))               
                if et > ctime and bt.date() >= ctime.date():
                    curepg.append(x)
                    
            for i, ep in enumerate(curepg):
                try:
                    ce = self.getControl(WMainForm.LBL_FIRST_EPG + i)
                    bt = datetime.datetime.fromtimestamp(float(ep['btime']))
                    et = datetime.datetime.fromtimestamp(float(ep['etime']))
                    if not ce:
                        raise
                    ce.setLabel(u"{0} - {1} {2}".format(bt.strftime("%H:%M"), et.strftime("%H:%M"), ep['name'].replace('&quot;', '"')))
                except:
                    break

            return True
                
        except Exception as e:
            log.e('showSimpleEpg error {}'.format(e))
        
        for i in range(99):
            try:
                ce = self.getControl(WMainForm.LBL_FIRST_EPG + i)
                if i == 0:
                    ce.setLabel('Нет программы')
                ce.setLabel('')
            except:
                break
        self.progress.setPercent(1)
            
            
    def onAction(self, action):                
        # log.d('Событие {0}'.format(action.getId()))  
        if action in WMainForm.CANCEL_DIALOG:
            log.d('ACTION CLOSE FORM')
            self.close() 
            
        if not self.IsCanceled():      
            if action.getButtonCode() == 61513:
                return
            elif action.getId() in WMainForm.ARROW_ACTIONS:
                log.d("ARROW_ACTION %s" % self.seltab)
                self.onFocus(self.getFocusId())
            elif action.getId() in WMainForm.CONTEXT_MENU_IDS and self.getFocusId() == WMainForm.CONTROL_LIST:
                if action.getId() == 101:
                    return
                self.showMenuWindow()
                
            elif action.getId() == WMainForm.ACTION_MOUSE:
                if (self.getFocusId() == WMainForm.CONTROL_LIST):
                    self.onFocus(WMainForm.CONTROL_LIST)
            elif action.getId() in WMainForm.DIGIT_BUTTONS:
                ############# IN PRESSING DIGIT KEYS ############
                self.channel_number_str += str(action.getId() - 58)                     
                self.select_channel(timeout=1)                
            else:
                super(WMainForm, self).onAction(action)
            
            self.hide_main_window(timeout=10)


    def updateList(self):
        def LoadOther():
            for thr in thrs:
                thrs[thr].join(10)
                
            for gr in self.channel_groups.getGroups():                    
                if gr not in [WMainForm.CHN_TYPE_ONETTVNET, WMainForm.CHN_TYPE_FAVOURITE]:
                    for cli in self.channel_groups.getChannels(gr):
                        self.channel_groups.delChannel(WMainForm.CHN_TYPE_ONETTVNET, cli.getProperty('id'))
                        
        self.showStatus("Получение списка каналов")
        self.list = self.getControl(WMainForm.CONTROL_LIST)
        for groupname in (WMainForm.CHN_TYPE_MODERATION, WMainForm.CHN_TYPE_FAVOURITE, WMainForm.CHN_TYPE_ONETTVNET):
            self.channel_groups.setGroup(groupname, '[COLOR FFFFFF00][B]' + groupname + '[/B][/COLOR]')
        thrs = {}
            
        thrs['channel'] = defines.MyThread(self.getChannels, 'channel')        
        thrs['moderation'] = defines.MyThread(self.getChannels, 'moderation')
        thrs['favourite'] = defines.MyThread(self.getChannels, 'favourite')
        thrs[WMainForm.CHN_TYPE_ONETTVNET] = defines.MyThread(self.getChannels, WMainForm.CHN_TYPE_ONETTVNET)
        
        for thr in thrs:
            thrs[thr].start()

        log.d('Ожидание результата')
        
        defines.MyThread(LoadOther).start()
        if self.cur_category not in (WMainForm.CHN_TYPE_MODERATION, WMainForm.CHN_TYPE_FAVOURITE, WMainForm.CHN_TYPE_ONETTVNET):
            thrs['channel'].join(10)
        elif self.cur_category in (WMainForm.CHN_TYPE_MODERATION):
            thrs['moderation'].join(10)
        elif self.cur_category in (WMainForm.CHN_TYPE_FAVOURITE):
            thrs['favourite'].join(10)              
        
        self.loadList()
    
    def loadList(self):
                
        log.d('updateList: Clear list')    
        self.list.reset()
        self.setFocus(self.getControl(WMainForm.BTN_CHANNELS_ID))
        self.img_progress.setVisible(False)
        self.hideStatus()
        log.d(self.selitem_id)
        

    def showStatus(self, text):
        log.d("showStatus: %s" % text)
        try:
            if self.img_progress: self.img_progress.setVisible(True)
            if self.txt_progress: self.txt_progress.setLabel(text)
            if self.infoform: self.infoform.printASStatus(text)
        except Exception as ex:
            log.w("showStatus error: {0}". format(ex))


    def showInfoStatus(self, text):
        if self.infoform: 
            self.infoform.printASStatus(text)


    def hideStatus(self):
        if self.img_progress: self.img_progress.setVisible(False)
        if self.txt_progress: self.txt_progress.setLabel("")


    def fillChannels(self):
        self.showStatus("Заполнение списка")
        if not self.list:
            self.showStatus("Список не инициализирован")
            return
        log.d('fillChannels: Clear list')
        self.list.reset()
        chnum_pattern = re.compile('^[0-9]+\.')
        
        if not self.channel_groups.getChannels(self.cur_category):            
            self.fillCategory()          
            self.hideStatus()
        else:
            li = xbmcgui.ListItem('..')
            self.list.addItem(li)
            for i, ch in enumerate(self.channel_groups.getChannels(self.cur_category)):
                chname = ch.getLabel()
                if not chnum_pattern.match(chname):
                    chname = "{0}. {1}".format(i + 1, ch.getLabel())
                    if ch.getProperty("access_user") == 0:
                        chname = "[COLOR FF646464]%s[/COLOR]" % chname
                    ch.setLabel(chname)
                self.list.addItem(ch)
            self.hideStatus()
            
            
    def fillTranslation(self):
        if not self.list:
            self.showStatus("Список не инициализирован")
            return
        self.showStatus("Заполнение списка")
        log.d('fillTranslation: Clear list')
        self.list.reset()
        for ch in self.translation:
            self.list.addItem(ch)
        self.hideStatus()


    def fillArchive(self):
        if not self.list:
            self.showStatus("Список не инициализирован")
            return
        log.d('fillArchive: Clear list')
        self.list.reset()
        for ch in self.archive:
            self.list.addItem(ch)
        log.d("fillArchive")


    def fillCategory(self):
        if not self.list:
            self.showStatus("Список не инициализирован")
            return
        log.d('fillCategory: Clear list')
        self.list.reset()
        for gr in self.channel_groups.getGroups():
            li = xbmcgui.ListItem(self.channel_groups[gr]["title"])
            li.setProperty('type', 'category')
            li.setProperty('id', '%s' % gr)
            self.list.addItem(li)


    def fillRecords(self, li, date=time.localtime()):
        self.showStatus("Загрузка архива")
        log.d('fillRecords: Clear list')
        self.list.reset()
        const_li = xbmcgui.ListItem("..")
        self.list.addItem(const_li)
        const_li = xbmcgui.ListItem("[COLOR FF0080FF]%s-%s-%s[/COLOR]" % (date.day, date.month, date.year))
        const_li.setProperty("type", "rec_date")
        const_li.setProperty("epg_cdn_id", li.getProperty("epg_cdn_id"))
        const_li.setProperty("date", "%s-%s-%s" % (date.year, date.month, date.day))
        self.list.addItem(const_li)
        
        try:
            data = defines.GET("http://{0}/v3/arc_records.php?session={1}&date={2}-{3}-{4}&epg_id={5}&typeresult=json".format(defines.API_MIRROR, self.session, date.day, date.month, date.year, li.getProperty("epg_cdn_id")), cookie=['PHPSESSID=%s' % self.session], trys=10)
            jdata = json.loads(data)
        except Exception as e:
            log.e('fillRecords error: {0}'.format(e))
            msg = "Ошибка Torrent-TV.RU"
            self.showStatus(msg)
            return
        
        if jdata["success"] == 0:
            self.showStatus(jdata["error"])
            return

        for rec in jdata["records"]:
            rec_date = time.localtime(float(rec["time"]))
            rec_li = xbmcgui.ListItem("[COLOR FFC0C0C0]%.2d:%.2d[/COLOR] %s" % (rec_date.tm_hour, rec_date.tm_min, rec["name"]), rec["name"], li.getProperty("icon"), li.getProperty("icon"))
            rec_li.setProperty("type", "record")
            rec_li.setProperty("id", '%s' % rec["record_id"])
            rec_li.setProperty("epg_cdn_id", '%s' % rec["epg_id"])
            rec_li.setProperty("icon", li.getProperty("icon"))
            self.list.addItem(rec_li)

        self.hideStatus()


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
        xbmcgui.WindowXML.close(self)
        

        

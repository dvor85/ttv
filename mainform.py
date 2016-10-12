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

from player import MyPlayer
from adswnd import AdsForm
from menu import MenuForm
from infoform import InfoForm
from dateform import DateForm
from ext.table import Channels as ExtChannels
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
        self.data.get(groupname)["channels"] = channels
        
    def addChannel(self, groupname, channel):
        if self.data.get(groupname):
            self.data.get(groupname).get("channels").append(channel)
        
    def del_channel_by_id(self, groupname, chid):
        chli = self.find_channel_by_id(groupname, chid)
        if chli:
            self.data.get(groupname).get("channels").remove(chli)
        
    def del_channel_by_name(self, groupname, name):
        chli = self.find_channel_by_name(groupname, name)
        if chli:
            self.data.get(groupname).get("channels").remove(chli)
                
    def getChannels(self, groupname):
        if self.data.get(groupname):
            return self.data.get(groupname).get("channels")
        
    def find_channel_by_id(self, groupname, chid):
        if self.data.get(groupname):
            for li in self.data.get(groupname).get("channels"):
                if li.getProperty('id') == chid and li.getProperty('access_user'):
                    return li  
            
    def find_channel_by_name(self, groupname, name):
        if self.data.get(groupname):
            for li in self.data.get(groupname).get("channels"):
                if li.getProperty('name').lower().strip() == name.lower().strip() and li.getProperty('access_user'):
                    return li
                
                
                
class RotateScreen(threading.Thread):    
    def __init__(self, img_control, screens):
        threading.Thread.__init__(self)
        self.active = False
        self.img_control = img_control
        self.screens = screens
        self.daemon = False
        
    def run(self):
        self.active = True
        while self.active:
            for screen in self.screens:
                if self.active:
                    self.img_control.setImage(screen['filename'])
                    for i in range(16):
                        if self.active:
                            xbmc.sleep(100)
                
    def stop(self):
        self.active = False
        self.img_control.setImage('')
            


class WMainForm(xbmcgui.WindowXML):
    CANCEL_DIALOG = (9, 10, 11, 92, 216, 247, 257, 275, 61467, 61448,)
    CONTEXT_MENU_IDS = (117, 101)
    ARROW_ACTIONS = (1, 2, 3, 4)
    DIGIT_BUTTONS = range(58, 68)
    ACTION_MOUSE = 107
    BTN_CHANNELS_ID = 102
    BTN_ARCHIVE_ID = 104
    BTN_VOD_ID = 113
    BTN_CLOSE = 101
    BTN_FULLSCREEN = 208
    IMG_SCREEN = 210
    IMG_LOGO = 1111
    CONTROL_LIST = 50
    PANEL_ADS = 105
    
    TXT_PROGRESS = 107
    IMG_PROGRESS = 108
    PROGRESS_BAR = 110
    
    BTN_INFO = 209
    LBL_FIRST_EPG = 300
    
    CHN_TYPE_FAVOURITE = 'Избранное'
    CHN_TYPE_MODERATION = 'На модерации'
    
    API_ERROR_INCORRECT = 'incorrect'
    API_ERROR_NOCONNECT = 'noconnect'
    API_ERROR_ALREADY = 'already'
    API_ERROR_NOPARAM = 'noparam'
    API_ERROR_NOFAVOURITE = 'nofavourite'    


    def __init__(self, *args, **kwargs):
        log.d('__init__')
        self.channel_groups = ChannelGroups()
        self.seltab = 0
        self.epg = {}
        self._re_1ttv_epg_text = re.compile('var\s+epg\s*=\s*(?P<e>\[.+?\])\s*;.*?</script>', re.DOTALL)
        self._re_1ttv_epg_json = re.compile('(?P<k>\w+)\s*:\s*(?P<v>.+?[,}])')
        self._re_url_match = re.compile('^(?:https?|ftps?|file)://')
        self.archive = []
        self.img_progress = None
        self.txt_progress = None
        self.list = None
        self.player = MyPlayer("player.xml", defines.SKIN_PATH, defines.ADDON.getSetting('skin'))
        self.player.parent = self
        self.amalkerWnd = AdsForm("adsdialog.xml", defines.SKIN_PATH, defines.ADDON.getSetting('skin'))
        self.load_selitem_info()            
        self.user = None
        self.infoform = None
        self.first_init = True
        self.session = None
        self.channel_number_str = ''
        
        self.select_timer = None
        self.hide_window_timer = None
        self.get_epg_timer = None
        self.show_screen_timer = None
        self.rotate_screen_thr = None
        
        self.initTTV()
        
    def initTTV(self):
        data = defines.GET('http://{0}/v3/version.php?application=xbmc&version={1}'.format(defines.API_MIRROR, defines.TTV_VERSION))
        try:
            jdata = json.loads(data)
            if defines.tryStringToInt(jdata.get('success')) == 0:                
                raise Exception(jdata.get('error'))
#             raise Exception('Test')    
        except Exception as e:
            log.e('onInit error: {0}'.format(e))
            msg = 'Ошибка Torrent-TV.RU'
            defines.showNotification(msg, xbmcgui.NOTIFICATION_ERROR)
            self.close()
            return
        if defines.tryStringToInt(jdata['support']) == 0:
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
            if defines.tryStringToInt(jdata.get('success')) == 0:                
                raise Exception(jdata.get('error'))
        except Exception as e:
            log.e('onInit error: {0}'.format(e))
            msg = 'Ошибка Torrent-TV.RU'
            defines.showNotification(msg, xbmcgui.NOTIFICATION_ERROR)
            self.close()             
            return
        
        self.user = {"login": defines.ADDON.getSetting('login'), "balance": jdata["balance"], "vip": jdata["balance"] > 1}
        
        self.session = jdata['session']
        
    
    def onInit(self):
        self.img_progress = self.getControl(WMainForm.IMG_PROGRESS)
        self.txt_progress = self.getControl(WMainForm.TXT_PROGRESS)
        self.progress = self.getControl(WMainForm.PROGRESS_BAR)
        self.list = self.getControl(WMainForm.CONTROL_LIST)
        self.init = True
        
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
        if self.rotate_screen_thr:
            self.rotate_screen_thr.stop()
        
        for controlId in (WMainForm.IMG_LOGO, WMainForm.IMG_SCREEN):
            self.getControl(controlId).setImage('')
            
        self.showNoEpg()
        if ControlID == WMainForm.CONTROL_LIST:
            if not self.list:
                return
            selItem = self.list.getSelectedItem()
            if selItem and not selItem.getLabel() == '..':
                epg_id = selItem.getProperty('epg_cdn_id')

                if self.epg.get(epg_id):
                    self.showEpg(epg_id)
                else:
                    self.getEpg(epg_id, timeout=0.5, callback=self.showEpg)
                
                self.showScreen(selItem.getProperty('id'), timeout=0.5)
                
                for controlId in (WMainForm.IMG_LOGO, WMainForm.IMG_SCREEN):
                    self.getControl(controlId).setImage(selItem.getProperty('icon'))
                
        
    def load_selitem_info(self):        
        self.cur_category = defines.ADDON.getSetting('cur_category')
        self.selitem_id = defines.ADDON.getSetting('cur_channel')
        if self.cur_category == '':
            self.cur_category = WMainForm.CHN_TYPE_FAVOURITE
        
        if self.selitem_id == '':
            self.selitem_id = -1 
        else:
            self.selitem_id = defines.tryStringToInt(self.selitem_id)
            
    
    def getFavourites(self):
        try:
            if defines.tryStringToInt(defines.FAVOURITE) == 0 and self.user["vip"]:
                jdata = favdb.RemoteFDB(self.session).get_json()
                if self.first_init and jdata and len(jdata['channels']) > 0:
                    favdb.LocalFDB().save(jdata['channels'])
                    self.first_init = False  
                return jdata
            else:
                return favdb.LocalFDB().get_json()                
                   
        except Exception as e:
            log.e('getFavourites error: {0}'.format(e))


    def getChannels(self, *args):
        param = args[0]

        log.d('getChannels {0}'.format(param))
        
        try:
            if param in ExtChannels.keys():                
                jdata = ExtChannels[param].get_json()              
            elif param == 'favourite':
                jdata = self.getFavourites() 
            else:
                data = defines.GET('http://{0}/v3/translation_list.php?session={1}&type={2}&typeresult=json'.format(defines.API_MIRROR, self.session, param), cookie=['PHPSESSID=%s' % self.session], trys=10)
                jdata = json.loads(data)
                
            if defines.tryStringToInt(jdata.get('success')) == 0:
                raise Exception(jdata.get('error'))            
        except Exception as e:
            log.e('getChannels error: {0}'.format(e))
            msg = "Ошибка Torrent-TV.RU"
            self.showStatus(msg)
            return
            
            
        for cat in jdata.get("categories", []):
            if not self.channel_groups.has_key('%s' % cat["id"]):
                self.channel_groups.setGroup('%s' % cat["id"], cat["name"])
        
        
        if jdata.get('channels'):
            for ch in jdata['channels']:
                if not (ch.get("name") or ch.get("id")):
                    continue
                if ch.get('logo'):
                    if not self._re_url_match.search(ch['logo']):                    
                        ch['logo'] = 'http://{0}/uploads/{1}'.format(defines.SITE_MIRROR, ch['logo'])    
                            
                li = xbmcgui.ListItem(ch["name"], '%s' % ch['id'], ch.get('logo'), ch.get('logo'))
                li.setProperty('name', ch["name"])
                li.setProperty('epg_cdn_id', '%s' % ch['epg_id'])
                li.setProperty('icon', ch.get('logo'))
                li.setProperty("type", "channel")
                li.setProperty("id", '%s' % ch["id"])
                li.setProperty("access_translation", '%s' % ch.get("access_translation"))
                li.setProperty("access_user", '%s' % ch.get("access_user"))
                
                if param == 'channel':
                    li.setProperty('commands', "%s" % (MenuForm.CMD_ADD_FAVOURITE))
                    self.channel_groups.addChannel('%s' % ch['group'], li)
                    
                elif param in ExtChannels.keys():
                    li.setProperty('commands', "%s" % (MenuForm.CMD_ADD_FAVOURITE))
                    self.channel_groups.addChannel(param, li)
                    
                elif param == 'moderation':
                    li.setProperty('commands', "%s" % (MenuForm.CMD_ADD_FAVOURITE))
                    self.channel_groups.addChannel(WMainForm.CHN_TYPE_MODERATION, li)
                            
                elif param == 'favourite':
                    li.setProperty('commands', "%s,%s,%s,%s" % (MenuForm.CMD_MOVE_FAVOURITE, MenuForm.CMD_DEL_FAVOURITE, MenuForm.CMD_DOWN_FAVOURITE, MenuForm.CMD_UP_FAVOURITE))
                    self.channel_groups.addChannel(WMainForm.CHN_TYPE_FAVOURITE, li)
                
                    
    def getArcChannels(self, *args):
        log.d('getArcChannels')
        try:
            data = defines.GET('http://{0}/v3/arc_list.php?session={1}&typeresult=json'.format(defines.API_MIRROR, self.session), cookie=['PHPSESSID=%s' % self.session], trys=10)
            jdata = json.loads(data)
            if defines.tryStringToInt(jdata.get('success')) == 0:
                raise Exception(jdata.get('error'))
        except Exception as e:
            log.e('getArcChannels error: {0}'.format(e))
            msg = "Ошибка Torrent-TV.RU"
            self.showStatus(msg)
            return
        
        self.archive = []
        
        for ch in jdata['channels']:
            if not (ch.get("name") or ch.get("id")):
                continue
            if ch.get('logo'):
                if not self._re_url_match.search(ch['logo']):                    
                    ch['logo'] = 'http://{0}/uploads/{1}'.format(defines.SITE_MIRROR, ch['logo'])    
            li = xbmcgui.ListItem(ch['name'], '%s' % ch["id"], ch.get("logo"), ch.get("logo"))
            li.setProperty("epg_cdn_id", '%s' % ch["epg_id"])
            li.setProperty("icon", ch.get("logo"))
            li.setProperty("type", "archive")
            li.setProperty('name', ch['name'])
            self.archive.append(li)


    def getEpg(self, epg_id, timeout=0, callback=None):
        def get():
            try:
                if epg_id and epg_id != '0':
                    log.d('getEpg->get')
                    self.showStatus('Загрузка программы')
                    
                    param = epg_id.split('=', 1)
                    if len(param) > 1:
                        if param[0] == 'channel':
                            self.epg[epg_id] = get_from_1ttv(param[1])
                        elif param[0] == 'title':
                            pass
                        else:
                            pass
                    else:
                        self.epg[epg_id] = get_from_api()                        
                            
                    self.hideStatus()
            except Exception as e:
                log.d('getEpg->get error: {0}'.format(e))
                
            if callback:
                callback(epg_id)
                    
        def get_from_api():  
            try:          
                data = defines.GET('http://{0}/v3/translation_epg.php?session={1}&epg_id={2}&typeresult=json'.format(defines.API_MIRROR, self.session, epg_id), cookie=['PHPSESSID=%s' % self.session], trys=1)
                jdata = json.loads(data)
                if defines.tryStringToInt(jdata.get('success')) != 0:
                    return jdata['data']  
             
            except Exception as e:
                log.d('getEPG->get_from_api error: {0}'.format(e))                 
                
        def get_from_1ttv(chid):        
            try:
                for tch in ExtChannels.itervalues():
                    chli = tch.find_by_id(chid)
                if chli:                    
                    http = defines.GET(chli.get('url'), trys=1)
                    m = self._re_1ttv_epg_text.search(http)
                    epgtext = self._re_1ttv_epg_json.sub('"\g<k>":\g<v>', m.group('e'))
                    epg = json.loads(epgtext)   
                    return epg 
            except Exception as e:
                log.d('getEPG->get_from_url error: {0}'.format(e))
            self.get_epg_timer = None
            
        if self.get_epg_timer:
            self.get_epg_timer.cancel()
            self.get_epg_timer = None
         
        self.get_epg_timer = threading.Timer(timeout, get)
        self.get_epg_timer.name = 'getEpg'
        self.get_epg_timer.daemon = False
        self.get_epg_timer.start()
        
        
    def getCurEpg(self, epg_id):
        try:        
            ctime = datetime.datetime.now()
            dt = (ctime - datetime.datetime.utcnow()) - datetime.timedelta(hours=3)
            
            prev_bt = 0
            prev_et = 0
            curepg = []
            for x in self.epg[epg_id]:                
                bt = datetime.datetime.fromtimestamp(float(x['btime']))
                et = datetime.datetime.fromtimestamp(float(x['etime']))               
                if et > ctime and abs((bt.date() - ctime.date()).days) <= 1 and prev_et <= float(x['btime']) > prev_bt:
                    curepg.append(x)
                    prev_bt = float(x['btime'])
                    prev_et = float(x['etime'])
            return curepg        
        
        except Exception as e:
            log.e('getCurEpg error {}'.format(e))
        
    
    def showEpg(self, epg_id=None):
        selitem = self.list.getSelectedItem()
        if selitem and selitem.getProperty('epg_cdn_id') == epg_id:
            try:       
                ctime = datetime.datetime.now()
                dt = (ctime - datetime.datetime.utcnow()) - datetime.timedelta(hours=3) 
                curepg = self.getCurEpg(epg_id)
                if len(curepg) > 0:                                        
                    for i, ep in enumerate(curepg):
                        try:
                            ce = self.getControl(WMainForm.LBL_FIRST_EPG + i)
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
                
                
    def showNoEpg(self):            
        for i in range(99):
            try:
                ce = self.getControl(WMainForm.LBL_FIRST_EPG + i)                
                if i == 0:
                    ce.setLabel('Нет программы')
                else:
                    ce.setLabel('')
            except:
                break
        self.progress.setPercent(1)
            
            
    def showScreen(self, cdn, timeout=0):
        def show():
            log.d('showScreen')
            if defines.tryStringToInt(cdn) > 0:             
                try:
                    count_screens = 2
                    data = defines.GET('http://{0}/v3/translation_screen.php?session={1}&channel_id={2}&typeresult=json&count={3}'.format(defines.API_MIRROR, self.session, cdn, count_screens), cookie=['PHPSESSID=%s' % self.session], trys=10)
                    jdata = json.loads(data)
                     
                    if defines.tryStringToInt(jdata.get('success')) != 0:
                        if self.rotate_screen_thr:  
                            self.rotate_screen_thr.stop()
                            self.rotate_screen_thr.join(0.2)
                            self.rotate_screen_thr = None
    
                        self.rotate_screen_thr = RotateScreen(self.getControl(WMainForm.IMG_SCREEN), jdata['screens'])
                        self.rotate_screen_thr.start()
                        
                except Exception as e:                
                    log.w('showScreen error: {0}'.format(e)) 
            self.show_screen_timer = None               
            
        if self.show_screen_timer:
            self.show_screen_timer.cancel()
            self.show_screen_timer = None
         
        self.show_screen_timer = threading.Timer(timeout, show)
        self.show_screen_timer.name = 'show_screen'
        self.show_screen_timer.daemon = False
        self.show_screen_timer.start()
        
        
    def updateList(self):
        def LoadOther():
            for thr in thrs.itervalues():
                thr.join(10)
            # удалить дубликаты каналов, присутствующих в оригинальном torrent-tv.    
            for gr in [x for x in self.channel_groups.getGroups() if x not in (WMainForm.CHN_TYPE_FAVOURITE)]: 
                for extgr in ExtChannels.iterkeys():           
                    if gr not in [x for x in ExtChannels.iterkeys() if x == extgr]:
                        for cli in self.channel_groups.getChannels(gr):
                            if not self.IsCanceled():
                                self.channel_groups.del_channel_by_id(extgr, cli.getProperty('id'))
                                self.channel_groups.del_channel_by_name(extgr, cli.getProperty('name'))
                        
        self.showStatus("Получение списка каналов")
        
        for groupname in [WMainForm.CHN_TYPE_MODERATION, WMainForm.CHN_TYPE_FAVOURITE]:
            self.channel_groups.setGroup(groupname, '[COLOR FFFFFF00][B]' + groupname + '[/B][/COLOR]')
        for groupname in ExtChannels.iterkeys():
            self.channel_groups.setGroup(groupname, '[COLOR FF00FF00][B]' + groupname + '[/B][/COLOR]') 

        thrs = {}
        thrs['channel'] = defines.MyThread(self.getChannels, 'channel')        
        thrs['moderation'] = defines.MyThread(self.getChannels, 'moderation')
        thrs['favourite'] = defines.MyThread(self.getChannels, 'favourite')
        thrs['archive'] = defines.MyThread(self.getArcChannels)
        for extgr in ExtChannels.iterkeys():  
            thrs[extgr] = defines.MyThread(self.getChannels, extgr)
        
        for thr in thrs.itervalues():
            thr.start()
            
        lo_thr = defines.MyThread(LoadOther)
        lo_thr.start()

        log.d('Ожидание результата')
        
        if self.cur_category not in [WMainForm.CHN_TYPE_MODERATION, WMainForm.CHN_TYPE_FAVOURITE] + ExtChannels.keys():
            thrs['channel'].join(10)
        elif self.cur_category in (WMainForm.CHN_TYPE_MODERATION):
            thrs['moderation'].join(10)
        elif self.cur_category in (WMainForm.CHN_TYPE_FAVOURITE):
            thrs['favourite'].join(10)         
        else:
            lo_thr.join(10)     
        
        self.loadList()
    
    
    def loadList(self):                
        log.d('updateList: Clear list')    
        self.list.reset()
        self.setFocusId(WMainForm.BTN_CHANNELS_ID)
        self.hideStatus()
        
    
    def checkButton(self, controlId):
        control = self.getControl(controlId)
        control.setLabel('>%s<' % control.getLabel())
        if self.seltab:
            btn = self.getControl(self.seltab)
            btn.setLabel(btn.getLabel().replace('<', '').replace('>', ''))
        self.seltab = controlId
        log.d('Focused %s %s' % (WMainForm.CONTROL_LIST, self.selitem_id))
        if (self.list) and (0 < self.selitem_id < self.list.size()):
            if self.first_init:  # автостарт канала
                self.first_init = False     
                self.startChannel()
               
    
    def startChannel(self):
        self.select_channel()
        self.LoopPlay()
        
                
    def select_channel(self, sch='', timeout=0):
        def clear():
            self.channel_number_str = ''
            self.select_timer = None
            
        if self.channel_number_str == '':
            self.channel_number_str = str(sch) if sch != '' else str(self.selitem_id) 
        chnum = defines.tryStringToInt(self.channel_number_str)                       
        log('CHANNEL NUMBER IS: %i' % chnum)              
        if 0 < chnum < self.list.size():            
            self.selitem_id = chnum
            self.setFocus(self.list)
            self.list.selectItem(self.selitem_id)          
                
        if self.select_timer:
            self.select_timer.cancel()
            self.select_timer = None      
        self.select_timer = threading.Timer(timeout, clear)
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
            self.hide_window_timer = None
        
        if self.hide_window_timer:
            self.hide_window_timer.cancel()
            self.hide_window_timer = None
        
        self.hide_window_timer = threading.Timer(timeout, hide)
        self.hide_window_timer.name = 'hide_main_window'
        self.hide_window_timer.daemon = False
        self.hide_window_timer.start()
                
            
    def onClickChannels(self):
        log.d('onClickChannels')
        self.fillChannels()
        if self.init:
            self.select_channel()
            self.init = False
        if self.seltab != WMainForm.BTN_CHANNELS_ID:
            self.checkButton(WMainForm.BTN_CHANNELS_ID)
            

    def onClickArchive(self):
        log.d('onClickArchive')
        self.fillArchive()
        if self.init:
            self.select_channel()
            self.init = False        
        if self.seltab != WMainForm.BTN_ARCHIVE_ID:
            self.checkButton(WMainForm.BTN_ARCHIVE_ID)
            
            
    def LoopPlay(self, *args):  
        while not self.IsCanceled():
            try: 
                selItem = self.list.getListItem(self.selitem_id)
                
                if defines.tryStringToInt(selItem.getProperty("access_user")) == 0:
                    access = selItem.getProperty("access_translation")
                    if access == "registred":
                        log.d("Трансляция доступна для зарегестрированных пользователей")
                    elif access == "vip":
                        log.d("Трансляция доступна для VIP пользователей")
                    else:
                        log.d("На данный момент трансляция не доступна")
                     
                buf = xbmcgui.ListItem(selItem.getLabel())
                buf.setProperty('epg_cdn_id', selItem.getProperty('epg_cdn_id'))
                buf.setProperty('icon', selItem.getProperty('icon'))
                buf.setProperty("type", selItem.getProperty("type"))
                buf.setProperty("id", selItem.getProperty("id"))
                buf.setProperty("name", selItem.getProperty("name"))
                
                if selItem.getProperty("type") == "archive":
                    self.fillRecords(buf, datetime.datetime.today())                
                    break
                defines.ADDON.setSetting('cur_category', self.cur_category)
                defines.ADDON.setSetting('cur_channel', str(self.selitem_id))
            
                self.player.Start(buf)
                
                if self.player.TSPlayer.manual_stopped:
                    break       
                if not self.IsCanceled():
                    xbmc.sleep(223)   
                    self.select_channel()  
                     
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
        elif xbmc.getCondVisibility("Window.IsVisible(12345)"):
            self.close()
            log.d("Is plugin Window")
        else:
            jrpc = json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"GUI.GetProperties","params":{"properties":["currentwindow"]},"id":1}'))
            if jrpc["result"]["currentwindow"]["id"] == 10025:
                log.d("Is video plugins window")
                self.close()
             
            
    def onClick(self, controlID):
        log.d('onClick %s' % controlID)
        if controlID == WMainForm.BTN_CHANNELS_ID: 
            self.onClickChannels()
               
        elif controlID == WMainForm.BTN_ARCHIVE_ID: 
            self.onClickArchive()
            
        elif controlID == 200: 
            self.setFocusId(WMainForm.CONTROL_LIST)
        elif controlID == WMainForm.CONTROL_LIST:
            selItem = self.list.getSelectedItem()           
            
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
                self.selitem_id = -1
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
                datefrm.doModal()
                for li in self.archive:
                    if li.getProperty("epg_cdn_id") == selItem.getProperty("epg_cdn_id"):
                        self.fillRecords(li, datefrm.date)
                        break
                else:
                    return
                self.fillRecords(self.archive[0], datefrm.date)
            
            self.selitem_id = self.list.getSelectedPosition()
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


    def showStatus(self, text):
        log.d("showStatus: %s" % text)
        try:
            if self.img_progress: self.img_progress.setVisible(True)
            if self.txt_progress: self.txt_progress.setLabel(text)
            if self.infoform: self.infoform.printASStatus(text)
        except Exception as e:
            log.w("showStatus error: {0}". format(e))


    def showInfoStatus(self, text):
        if self.infoform: 
            self.infoform.printASStatus(text)


    def hideStatus(self):
        try:
            if self.img_progress: 
                self.img_progress.setVisible(False)
            if self.txt_progress: 
                self.txt_progress.setLabel("")
        except Exception as e:
            log.w("hideStatus error: {0}". format(e))


    def fillChannels(self):
        self.showStatus("Заполнение списка")
        if not self.list:
            self.showStatus("Список не инициализирован")
            return
        log.d('fillChannels: Clear list')
        self.list.reset()
        
        if not self.channel_groups.getChannels(self.cur_category):            
            self.fillCategory()          
            self.hideStatus()
        else:
            li = xbmcgui.ListItem('..')
            self.list.addItem(li)
            for i, ch in enumerate(self.channel_groups.getChannels(self.cur_category)):
                chname = "{0}. {1}".format(i + 1, ch.getProperty('name'))
                if defines.tryStringToInt(ch.getProperty("access_user")) == 0:
                    chname = "[COLOR FF646464]%s[/COLOR]" % chname
                ch.setLabel(chname)
                self.list.addItem(ch)
            self.hideStatus()
            
            
    def fillArchive(self):
        if not self.list:
            self.showStatus("Список не инициализирован")
            return
        log.d('fillArchive: Clear list')
        self.list.reset()
        for i, ch in enumerate(self.archive):
            chname = "{0}. {1}".format(i + 1, ch.getProperty('name'))
            ch.setLabel(chname)
            self.list.addItem(ch)
        log.d("fillArchive")


    def fillCategory(self):
        def AddItem(groupname):
            li = xbmcgui.ListItem(self.channel_groups[groupname]["title"])
            li.setProperty('type', 'category')
            li.setProperty('id', '%s' % groupname)
            self.list.addItem(li)
            
        if not self.list:
            self.showStatus("Список не инициализирован")
            return
        log.d('fillCategory: Clear list')
        self.list.reset()
        for gr in ExtChannels.iterkeys():
            AddItem(gr)
        for gr in [WMainForm.CHN_TYPE_FAVOURITE, WMainForm.CHN_TYPE_MODERATION]:
            AddItem(gr)
        for gr in self.channel_groups.getGroups():
            if gr not in ExtChannels.keys() + [WMainForm.CHN_TYPE_FAVOURITE, WMainForm.CHN_TYPE_MODERATION]:
                AddItem(gr)


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
            if defines.tryStringToInt(jdata.get('success')) == 0:
                raise Exception(jdata.get("error"))
            
            for rec in jdata["records"]:
                rec_date = time.localtime(float(rec["time"]))
                rec_li = xbmcgui.ListItem("[COLOR FFC0C0C0]%.2d:%.2d[/COLOR] %s" % (rec_date.tm_hour, rec_date.tm_min, rec["name"]), rec["name"], li.getProperty("icon"), li.getProperty("icon"))
                rec_li.setProperty("type", "record")
                rec_li.setProperty("id", '%s' % rec["record_id"])
                rec_li.setProperty("epg_cdn_id", '%s' % rec["epg_id"])
                rec_li.setProperty("icon", li.getProperty("icon"))
                self.list.addItem(rec_li)
        except Exception as e:
            log.e('fillRecords error: {0}'.format(e))
            msg = "Ошибка Torrent-TV.RU"
            self.showStatus(msg)

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
        if self.rotate_screen_thr:
            self.rotate_screen_thr.stop()    
        
        xbmcgui.WindowXML.close(self)
        

        

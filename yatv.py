# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

import datetime
import time
import utils
import defines
import logger
from threading import Event

import os
try:
    import simplejson as json
except ImportError:
    import json


fmt = utils.fmt
log = logger.Logger(__name__)
_servers = ['api.torrent-tv.ru', '1ttvxbmc.top']


class YATV():
    _instance = None
    _lock = Event()
    _xml_lib = 0

    @staticmethod
    def get_instance():
        if YATV._instance is None:
            if not YATV._lock.is_set():
                YATV._lock.set()
                try:
                    YATV._instance = YATV()
                except Exception as e:
                    log.error(fmt("get_instance error: {0}", e))
                    YATV._instance = None
                finally:
                    YATV._lock.clear()
        return YATV._instance

    def __init__(self):
        self.channels = {}
        self.jdata = None
        log.d('start initialization')
        self.yatv_file_json = os.path.join(defines.CACHE_PATH, 'yatv.json')

        same_date = False
        if os.path.exists(self.yatv_file_json):
            same_date = datetime.date.today() == datetime.date.fromtimestamp(os.path.getmtime(self.yatv_file_json))

        if not os.path.exists(self.yatv_file_json) or not same_date:
            if os.path.exists(self.yatv_file_json):
                os.unlink(self.yatv_file_json)
            bt = time.time()
            self.update_yatv()
            log.d(fmt("Loading yatv in {t} sec", t=time.time() - bt))
        if not self.jdata:
            with open(self.yatv_file_json, 'rb') as fp:
                self.jdata = json.load(fp)

        log.d('stop initialization')

    def update_yatv(self):
        ncrd = str(long(time.time()) * 1000 + 1080)
        dtm = time.strftime('%Y-%m-%d')

        Lcnl = (1867, 1861, 1856, 1853, 1852, 1845, 1844, 1843, 1842, 1841, 1838, 1834, 1828, 1827, 1821, 1820, 1817, 1816, 1815, 1814, 1810, 1809, 1808, 1807, 1806, 161, 1804, 1803, 1802, 1799, 1798, 1794, 1793, 1790, 1785, 1784, 1783, 1782, 1781, 1780, 1778, 1767, 1773, 1772, 1766, 1765, 1764, 1763, 1762, 1761, 1760, 1759, 1757, 1755, 1754, 1753, 690, 1744, 1743, 1746, 1738, 1737, 1734, 1736, 1732, 1731, 1727, 1728, 1730, 1729, 1726, 1725, 1721, 1723, 1722, 1720, 1716, 1714, 1702, 1719, 1713, 1703, 1698, 1700, 1699, 932, 1666, 363, 248, 180, 509, 730, 1396, 576, 141, 37, 6, 783, 275, 618, 1425, 217, 638, 349, 431, 933, 626, 442, 756, 1672, 1670, 1663, 1657, 1681, 1588, 1586, 423, 1038, 741, 138, 1377, 1395, 389, 1612, 1011, 1012, 331, 1043, 1042, 1034, 1031, 984, 1035, 1372, 1013, 983, 987, 807, 124, 1033, 382, 934, 464, 1030, 560, 990, 930, 415, 121, 801, 631, 312, 1676, 920, 663, 1329, 1026, 925, 165, 412, 777, 1322, 1679, 1662, 1660, 1397, 425, 776, 1571,
                173, 505, 919, 661, 617, 779, 346, 595, 547, 21, 113, 931, 153, 614, 637, 705, 376, 434, 132, 82, 393, 257, 491, 156, 680, 25, 662, 1021, 151, 681, 927, 258, 591, 642, 533, 319, 715, 575, 59, 589, 1331, 315, 355, 461, 247, 23, 495, 463, 313, 921, 214, 384, 831, 278, 502, 743, 828, 1578, 1332, 66, 810, 494, 31, 917, 601, 555, 929, 308, 410, 567, 1669, 1668, 1667, 1376, 664, 1039, 454, 850, 737, 288, 455, 563, 481, 328, 406, 250, 1585, 669, 1562, 1365, 685, 769, 223, 757, 765, 1436, 1330, 1394, 521, 277, 325, 365, 102, 409, 912, 613, 996, 35, 273, 1036, 928, 322, 367, 333, 774, 723, 648, 520, 794, 675, 55, 924, 1680, 1620, 1674, 799, 1584, 834, 798, 608, 644, 12, 1570, 352, 516, 686, 659, 821, 518, 485, 53, 311, 309, 918, 1037, 1371, 935, 615, 994, 401, 477, 125, 145, 566, 542, 22, 462, 123, 267, 127, 1046, 1335, 100, 323, 898, 1649, 1598, 150, 897, 633, 726, 405, 1003, 279, 304, 79, 447, 689, 529, 1000, 740, 1683, 187, 427, 162, 1593, 597, 146, 1171)

        channelIds = ''  # 'channelIds%22%3A%22'
        for i in Lcnl:
            channelIds += str(i) + '%2C'
        channelIds = channelIds[:-3]  # +'%22'
        with open(self.yatv_file_json, 'wb') as fp:
            fp.write('[')
        m = 2
        for n in range(0, m):
            url = 'https://m.tv.yandex.ru/ajax/i-tv-region/get?params=%7B"channelLimit"%3A10%2C"channelOffset"%3A' + str(n * 10) + '%2C"fields"%3A"channel%2Ctitle%2Cchannel%2Cid%2Ctitle%2Clogo%2Csizes%2Cwidth%2Cheight%2Csrc%2Ccopyright%2Cschedules%2Cchannels%2Cchannel%2Cid%2Ctitle%2CavailableProgramTypes%2Celement%2Cid%2Cname%2Cevents%2Cid%2CchannelId%2Cepisode%2Cdescription%2CseasonName%2CseasonNumber%2Cid%2CprogramId%2Ctitle%2Cstart%2Cfinish%2Cprogram%2Cid%2Ctype%2Cid%2Cname%2Ctitle"%2C"channelIds"%3A"' + \
                channelIds + '"%2C"start"%3A"' + dtm + \
                'T03%3A00%3A00%2B03%3A00"%2C"duration"%3A96400%2C"channelProgramsLimit"%3A500%2C"lang"%3A"ru"%7D&userRegion=193&resource=schedule&ncrd=' + ncrd
            try:
                r = defines.request(url)
#                 self.jdata = r.json()
                with open(self.yatv_file_json, 'ab') as fp:
                    fp.write(r.content)
                    if n < m - 1:
                        fp.write(',')
#                     json.dump(self.jdata, fp, indent=4)
            except Exception as e:
                log.error(fmt('update_yatv error: {0}', e))
        with open(self.yatv_file_json, 'ab+') as fp:
            fp.write(']')
            fp.seek(0)
            self.jdata = json.load(fp)

    def strptime(self, date_string):
        try:
            return datetime.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
        except TypeError:
            return datetime.datetime(*(time.strptime(date_string, "%Y-%m-%dT%H:%M:%S")[0:6]))

    def get_epg_by_id(self, chid):
        if chid is None:
            return
        ctime = datetime.datetime.now()
        offset = int(round((ctime - datetime.datetime.utcnow()).total_seconds()) / 3600)
        for p in self.jdata:
            for sch in p['schedules']:
                if sch['channel']['id'] == chid:
                    for evt in sch['events']:
                        ep = {}

                        bt = evt['start'].split('+')
                        bt = self.strptime(bt[0]) + datetime.timedelta(hours=-3 + offset)
                        ep['btime'] = time.mktime(bt.timetuple())

                        et = evt('finish').split('+')
                        et = self.strptime(et[0]) + datetime.timedelta(hours=-3 + offset)
                        ep['etime'] = time.mktime(et.timetuple())

                        ep['name'] = evt['program']['title']

                        yield ep
                    break

    def get_id_by_name(self, name):
        name = utils.lower(name, 'utf8')
        for sch in self.jdata['schedules']:
            if utils.lower(sch['channel']['title'], 'utf8') == name:
                return sch['channel']['id']

    def get_epg_by_name(self, name):
        return self.get_epg_by_id(self.get_id_by_name(name))


if __name__ == '__main__':
    pass

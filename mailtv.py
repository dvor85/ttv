# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import datetime
import gzip
import json
import os
import re
import time
from threading import Event, Lock, Semaphore
import requests
import defines
import logger
from sources.channel_info import CHANNEL_INFO
from utils import uni, str2int, fs_str, makedirs
from six import itervalues


log = logger.Logger(__name__)
_name_offset_regexp = re.compile(r'\s*(?P<name>.*?)\s*\((?P<offset>[\-+]+\d)\)\s*')


def strptime(date_string, _format="%Y-%m-%dT%H:%M:%S"):
    try:
        return datetime.datetime.strptime(uni(date_string), _format)
    except TypeError:
        return datetime.datetime(*(time.strptime(uni(date_string), _format)[0:6]))


def get_name_offset(name):
    name_offset = _name_offset_regexp.search(name)
    if name_offset:
        return name_offset.group('name'), str2int(name_offset.group('offset'))
    else:
        return name, None


class MAILTV:
    _instance = None
    _lock = Event()

    @staticmethod
    def get_instance():
        if MAILTV._instance is None:
            if not MAILTV._lock.is_set():
                MAILTV._lock.set()
                try:
                    MAILTV._instance = MAILTV()
                except Exception as e:
                    log.error("get_instance error: {0}".format(e))
                    MAILTV._instance = None
                finally:
                    MAILTV._lock.clear()
        return MAILTV._instance

    def __init__(self):
        log.d('start initialization')
        self.jdata = {}
        self.update_timer = None
        self.mailtv_path = os.path.join(defines.CACHE_PATH, 'mailtv')
        self.mailtv_logo_path = os.path.join(defines.CACHE_PATH, 'logo')
        self.sess = requests.Session()
        self.lock = Lock()
        self.sema = Semaphore(8)
        makedirs(fs_str(self.mailtv_path))

        self.limit_channels = 24
        self.pages = int(round(len(self.get_availible_channels()) / self.limit_channels))
        self.get_jdata()

        log.d('stop initialization')

    def get_jdata(self):
        threads = []
        bt = time.time()
        with self.lock:
            for page in range(0, self.pages):
                if defines.isCancel():
                    return
                threads.append(defines.MyThread(self.update_mailtv, page=page))

            for t in threads:
                t.start()
            for t in threads:
                t.join()
        log.d("Loading mailtv in {t} sec".format(t=time.time() - bt))
        return self.jdata

    def update_mailtv(self, page=0):

        mailtv_file = os.path.join(self.mailtv_path, "{0}.gz".format(page))
        valid_date = os.path.exists(fs_str(mailtv_file)) and \
            datetime.date.today() == datetime.date.fromtimestamp(os.path.getmtime(fs_str(mailtv_file)))
        if not valid_date:
            ncrd = uni(int(time.time()) * 1000 + 1080)
            dtm = uni(time.strftime('%Y-%m-%d'))

            url = 'https://tv.mail.ru/ajax/index/'
            # """
            # https://tv.yandex.ru/ajax/i-tv-region/get?params={"duration":96400,"fields":"schedules,channel,title,id,events,channelId,start,finish,program,availableChannels,availableChannelsIds"}&resource=schedule&lang=ru&userRegion=193
            # """
            _b = page * self.limit_channels
            if _b >= len(self.get_availible_channels()):
                return
            _f = (page + 1) * self.limit_channels
            if _f >= len(self.get_availible_channels()):
                _f = len(self.get_availible_channels()) - 1

            _params = {"region_id": 70,
                       "channel_type": "all",
                       "appearance": "list",
                       "period": "all",
                       "date": dtm,
                       "ex": self.get_availible_channels()[_b:_f]
                       }

            with self.sema:
                with gzip.open(fs_str(mailtv_file), 'wb') as fp:
                    try:
                        r = defines.request(url, method='post', params=_params, session=self.sess,
                                            headers={'Referer': 'https://tv.mail.ru/'})
                        fp.write(r.content)
                        self.jdata[page] = r.json()
                    except Exception as e:
                        log.error('update_mailtv error: {0}'.format(e))
        if page not in self.jdata:
            try:
                bt = time.time()
                with gzip.open(fs_str(mailtv_file), 'rb') as fp:
                    self.jdata[page] = json.load(fp)
                log.d("Loading mailtv json from {y} in {t} sec".format(y=mailtv_file, t=time.time() - bt))
            except Exception as e:
                log.e("Error while loading json from {y}: {e}".format(y=mailtv_file, e=uni(e)))
                if os.path.exists(fs_str(mailtv_file)):
                    os.unlink(fs_str(mailtv_file))

    def get_sess(self):
        return self.sess

    def get_availible_channels(self):
        return [2430, 1117, 2060, 1395, 3128, 1169, 1112, 3126, 3127, 1051, 2519, 2068, 3129, 1671, 963, 968, 986, 2338, 1126,
                1162, 1049, 1259, 717, 1111, 3033, 1193, 2811, 713, 743, 1234, 734, 1263, 933, 2273, 775, 1334, 864, 2727, 1799,
                2728, 2729, 1219, 1894, 2274, 1201, 1827, 796, 1810, 2470, 736, 1136, 1197, 1243, 1027, 1144, 1653, 1075, 1362,
                1115, 889, 1397, 1800, 1944, 2121, 2123, 2384, 800, 1566, 1718, 1926, 742, 2154, 2777, 905, 980, 1066, 1143,
                1552, 2122, 1063, 1396, 1266, 1477, 1528, 1567, 1574, 1628, 919, 924, 1195, 1244, 1282, 1296, 1307, 1353, 1356,
                1002, 1003, 2150, 1019, 1094, 1122, 2136, 2808, 1588, 729, 744, 868, 761, 975, 763, 1008, 801, 1092, 911, 787,
                2134, 2186, 781, 732, 1454, 896, 2137, 769, 833, 1141, 1269, 2383, 1651, 1249, 1038, 808, 1258, 1716, 814, 1503,
                1739, 838, 1669, 2677, 907, 1780, 929, 1991, 2806, 1050, 945, 2090, 2048, 1004, 2277, 1007, 2737, 1083, 2739,
                1085, 2875, 1097, 1103, 1134, 2311, 1159, 1384, 2097, 1241, 1684, 715, 2740, 1343, 888, 1721, 994, 2281, 1064,
                1229, 1309, 1340, 1300, 1612, 2135, 834, 853, 901, 942, 953, 1057, 1104, 1127, 1129, 1182, 1185, 974, 1346,
                2111, 1449, 2166, 1570, 2276, 810, 2741, 822, 1010, 2742, 745, 766, 806, 1252, 1324, 1326, 2743, 1354, 1381, 1516,
                1666, 1576, 1693, 1603, 1262, 1968, 1367, 2246, 2404, 2717, 2744, 2682, 2622, 2745, 2746, 2180, 2747, 1436,
                2672, 2748, 2368, 1433, 2615, 1825, 2007, 1405, 2736, 2301, 1741, 2458, 2349, 1319, 2681, 2711, 2716, 2869,
                1660, 2304, 2749, 2876, 2367, 1707, 1993, 2771, 2750, 2873, 2874, 921, 2698, 1956, 1727, 1524, 1798, 2168,
                1070, 1470, 1479, 1579, 1598, 1832, 2174, 1781, 1784, 2179, 2194, 1702,
                2399, 2006, 1683, 2680, 2214, 1744, 2215, 1806, 2288, 1818, 2291, 1829, 2295, 2309, 2303, 2310, 2305, 2293,
                773, 2321, 2306, 2325, 1116, 2348, 2353, 2893, 1401, 2452, 1542, 2674, 1700, 1557, 1385, 2616, 1813, 1559,
                2676, 2854, 2290, 2705, 1590, 2678, 2124, 1618, 2735, 2294, 1619, 1422, 1817, 2259, 1617, 1809, 2244, 2300,
                2794, 739, 2181, 1257, 1511, 2463, 2161, 981, 2202, 1101, 2237, 1250, 2296, 2457, 1404, 2339, 2465, 1521,
                2341, 1572, 2324, 2401, 1352, 2261, 2356, 2423, 1380, 2279, 2425, 2701, 1622, 2751, 2702, 2207, 2868, 2263,
                2979, 2894, 2351, 3153, 2987, 3011, 2424, 1408, 1610, 2116, 1831, 873, 904, 2486, 832, 2113, 2280, 2115,
                2427, 726, 2456, 2802, 1836, 1794, 786, 1834, 1884, 2731, 2613, 2264, 2753, 2772, 1333, 2976, 2035, 835,
                2195, 2693, 2285, 2922, 2258, 2406, 2407, 2487, 2507, 2197, 2396, 2669, 2224, 2411, 2726, 2416, 2721, 2977,
                2426, 2983, 1821, 1835, 3171, 2437, 3172, 2445, 2447, 2448, 2450, 2981, 1786, 2011, 2200, 1851, 2175, 1871,
                2468, 3179, 2823, 1204, 2856, 2386, 2859, 2420, 2882, 1811, 2919, 3111, 3137, 3138, 2451, 2212, 3139, 2810,
                2446, 2204, 3141, 3108, 2724, 2704, 3140, 2775, 3142, 2798, 3161, 2805, 2173, 3177, 2807, 2216, 3178, 2820,
                1854, 1128, 2206, 1882, 1561, 1759, 1787, 2153, 3123, 2217, 2994, 3159, 782, 1378, 2326, 2795, 3169, 2865,
                3117, 3154, 3163, 3168, 1420, 2024, 2755, 2756, 3155, 3156, 3157, 3158, 2042, 1658, 2243, 2252, 2369, 3118,
                2844, 2863, 2871, 2881, 3032, 1717, 2044, 2198, 2249, 2232, 2832, 927, 1754, 943, 1840, 1014, 1872, 1023,
                1921, 1096, 1961, 1156, 2008, 1174, 2015, 1179, 2043, 1255, 2673, 1429, 2885, 1624, 1633, 1637, 1302,
                1638, 2916, 1714, 1732]

        # return [850, 1271, 1395, 1389, 1139, 2060, 1112, 1158, 751, 1051, 2068, 1383, 986, 963, 968, 1671, 1259, 1049, 717, 1162, 2097, 2338, 1670, 1193,
        # 1973, 24, 843, 732, 2360, 2391, 1959, 2373, 743, 1173, 2273, 933, 1334, 1799, 736, 1362, 800, 868, 975, 1008, 1092, 2186, 2025, 1340,
        # 1462, 1519, 1612, 888, 994, 1063, 1064, 1229, 1309, 1968, 1042, 1433, 2007, 1727, 1956, 2355, 2266, 2396, 1835, 713, 1234, 1607, 864, 1405,
        # 1810, 1066, 1143, 2120, 2122, 2123, 2384, 742, 905, 980, 1300, 1721, 1782, 2301, 2368, 2294, 2399, 2263, 2351, 1851, 775, 1219, 1894, 2274,
        # 1243, 889, 1944, 919, 924, 1195, 1244, 1282, 1296, 1307, 1353, 1356, 1396, 1477, 1567, 1628, 1122, 2136, 729, 761, 763, 792, 801, 911,
        # 1002, 1003, 1019, 1094, 896, 2137, 1050, 2048, 2167, 2281, 1266, 1333, 1343, 1707, 1993, 2350, 2324, 2356, 2425, 2035, 2195, 2285, 2363, 2375,
        # 2413, 2173, 2216, 2153, 2243, 1027, 1800, 1566, 1718, 1926, 2154, 796, 1144, 773, 787, 833, 1269, 1651, 769, 1085, 1097, 1103, 1134, 1159,
        # 1201, 1241, 808, 1249, 814, 1258, 838, 1503, 907, 1669, 929, 1780, 945, 1991, 1004, 2090, 1007, 2277, 1083, 2135, 2193, 2268, 2111, 2166,
        # 2276, 974, 921, 1010, 1262, 1342, 1367, 1397, 2246, 2404, 1653, 2300, 2269, 2194, 2306, 2353, 2209, 2214, 2215, 2235, 2288, 2291, 2295, 2303,
        # 2305, 2259, 2205, 2210, 2400, 2401, 2423, 2161, 2202, 2237, 2296, 2339, 2341, 2398, 1794, 2192, 2211, 2258, 2407, 2411, 2199, 2200, 2191, 2234,
        # 1641, 1658, 2044, 2198, 2249, 2252, 1126, 1197, 1352, 1380, 1499, 1610, 1622, 835, 900, 944, 1075, 1115, 1525, 1827, 781, 996, 1136, 1141,
        # 1204, 1384, 1623, 1684, 726, 739, 1420, 2290, 2420, 1834, 2386, 1813, 2010, 1747, 2311, 1576, 1603, 745, 766, 806, 1252, 1324, 1326, 1354,
        # 1381, 1516, 2006, 2424, 1825, 2197, 2224, 2416, 2426, 2212, 2155, 2042, 1970, 1971, 1972, 715, 1038, 1716, 1739, 1185, 1346, 810, 1449, 822,
        # 1570, 834, 853, 901, 942, 953, 1057, 1104, 1111, 1127, 1129, 1182, 2317, 2367, 1660, 2304, 2293, 2325, 1831, 2026, 2280, 2264, 2405, 2415,
        # 2217, 2024, 1787, 782, 946, 1128, 1302, 1378, 1759, 2326, 1778, 1652, 2262, 2298, 2320, 2206, 1666, 1687, 904, 1579, 981, 1590, 1070, 1617,
        # 1116, 1618, 1250, 1619, 1257, 1657, 1360, 1683, 1401, 2124, 1404, 2204, 1408, 2227, 1422, 1521, 1542, 786, 1557, 832, 1559, 873, 1832, 1479,
        # 1524, 1598, 2174, 1470, 1783, 1818, 2113, 2116, 2115, 1700, 2180, 1781, 1784, 1817, 1741, 1786, 1806, 2160, 2244, 2309, 2310, 2321, 2348, 2349,
        # 2383, 1798, 2168, 1702, 1830, 2179, 1744, 1511, 2207, 2260, 2261, 2427, 1836, 1884, 1821, 2011, 2175, 1871, 1854, 2226, 2229, 2230, 1723, 2232,
        # 2369, 1385, 1263, 1366, 1801, 1561, 1574, 943, 1382, 1507, 1528, 714,
        # 744, 1014, 1023, 1096, 1174, 1714, 950, 1255, 1429, 1624, 927, 1179]

    def get_epg_by_id(self, chid, epg_offset=None):
        if chid is None:  # or chid not in self.availableChannels["availableChannelsIds"]:
            return
        ctime = datetime.datetime.now()
        offset = round((ctime - datetime.datetime.utcnow()).total_seconds() / 3600) if epg_offset is None else epg_offset
        # bt = datetime.datetime.fromordinal((ctime.date().toordinal()))
        bt = None
        ep = None
        for p in itervalues(self.get_jdata()):
            for sch in p['schedule']:
                if sch['channel']['id'] == chid:
                    for evt in sch['event']:

                        bt = map(int, evt['start'].split(':'))
                        bt = datetime.datetime.fromordinal(
                            (ctime.date().toordinal())) + datetime.timedelta(hours=bt[0], minutes=bt[1]) + datetime.timedelta(hours=-3 + offset)
                        # if et is None:
                        # continue
                        if ep is not None:
                            ep['etime'] = time.mktime(bt.timetuple())
                        ep = {}

                        ep['btime'] = time.mktime(bt.timetuple())

                        #et = strptime(et[0]) + datetime.timedelta(hours=-3 + offset)
                        # ep['etime'] = time.mktime(et.timetuple())
                        ep['name'] = evt['name']
                        # ep['desc'] = evt['program'].get('description', '')
                        if 'images' in evt:
                            ep['screens'] = ['http:{src}'.format(src=x['sizes']['200']['src']) for x in evt['program']['images']]

                        yield ep

    def get_id_by_name(self, name):
        names = [name.lower()]
        names.extend(CHANNEL_INFO.get(names[0], {}).get("aliases", []))
        for p in itervalues(self.get_jdata()):
            for sch in p['schedule']:
                if sch['channel']['name'].lower() in names:
                    return sch['channel']['id']

    def get_epg_by_name(self, name):
        name_offset = get_name_offset(name)
        return self.get_epg_by_id(self.get_id_by_name(name_offset[0]), name_offset[1])

    def get_logo_by_id(self, chid):
        if chid is None:  # or chid not in self.availableChannels["availableChannelsIds"]:
            return ''
        for p in itervalues(self.get_jdata()):
            for sch in p['schedule']:
                if sch['channel']['id'] == chid:
                    if 'pic_url' in sch['channel']:
                        return sch['channel']['pic_url']
        return ''

    def get_logo_by_name(self, name):
        name_offset = get_name_offset(name)
        return self.get_logo_by_id(self.get_id_by_name(name_offset[0]))


if __name__ == '__main__':
    pass

# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru

from __future__ import absolute_import, division, unicode_literals

import datetime
import gzip
import json
import os
import time
from threading import Event, Lock, Semaphore
import requests
import defines
import logger
from sources.channel_info import CHANNEL_INFO
from utils import uni, fs_str
from six import itervalues
from epgs.epgtv import EPGTV
import re


log = logger.Logger(__name__)
_tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')


class MAILTV(EPGTV):
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
        EPGTV.__init__(self, 'mailtv')
        self.jdata = {}
        self.update_timer = None

        self.sess = requests.Session()
        self.lock = Lock()
        self.sema = Semaphore(8)

        self.channels = [
            [],
            [2430, 1117, 2060, 1395, 3128, 1169, 1112, 3126, 3127, 1051, 2519, 2068, 3129, 1671, 963, 968, 986, 1126, 2338, 1162, 1049, 1800, 1259, 3033],
            [717, 2097, 1111, 1193, 1201, 796, 3161, 787, 1144, 2150, 743, 1653, 2384, 2811, 734, 1263, 713, 775, 1367, 1397, 933, 1794, 2273, 2090],
            [1007, 1234, 1004, 2470, 1991, 1334, 864, 1219, 1894, 2274, 1799, 2727, 2728, 2729, 1552, 1810, 1027, 1780, 736, 1136, 1827, 808, 945, 889],
            [1362, 1075, 1944, 905, 929, 1269, 800, 2154, 1588, 2134, 1143, 1566, 2777, 1718, 742, 1266, 919, 924, 1195, 1244, 732, 1282, 2290, 3159],
            [1296, 2404, 1307, 1926, 1353, 2717, 1356, 1396, 1567, 1574, 1628, 1063, 2136, 2808, 729, 2983, 761, 3142, 763, 801, 911, 868, 1002, 975],
            [1003, 1008, 1019, 1092, 1094, 1122, 2427, 2669, 2977, 2979, 1319, 3140, 1115, 2123, 2186, 2383, 769, 896, 2122, 3108, 1825, 1050, 814, 715],
            [2048, 833, 1038, 838, 1716, 2121, 921, 1739, 1083, 2677, 1103, 1134, 2737, 1159, 1241, 1258, 1651, 2044, 2875, 1343, 2507, 1721, 2726, 2281],
            [3153, 2135, 888, 994, 1066, 1064, 1300, 907, 1229, 1010, 1309, 1085, 1340, 1097, 1612, 1249, 1262, 1503, 1669, 2246, 2423, 2487, 2311, 1449],
            [1570, 810, 2368, 822, 2739, 834, 853, 901, 942, 953, 1057, 1104, 1127, 1129, 1182, 1185, 1346, 980, 2740, 2137, 2741, 745, 766, 806],
            [1252, 1666, 1324, 1693, 1326, 1354, 1381, 1516, 1576, 1603, 2742, 1968, 781, 1528, 1684, 2622, 2682, 2743, 2744, 2294, 1384, 2180, 2745, 1436],
            [2672, 2746, 1433, 2711, 2007, 2367, 2716, 2869, 1405, 1707, 2747, 1660, 1993, 1741, 2301, 2615, 2349, 2458, 2736, 2304, 2681, 2771, 2748, 2698],
            [2873, 2874, 2749, 2351, 2750, 1851, 1727, 1956, 1524, 1798, 2214, 2168, 2215, 2353, 2277, 1579, 2876, 1598, 3118, 1832, 3155, 2174, 3156, 3157],
            [2263, 1070, 1470, 1479, 3158, 974, 1702, 1781, 1784, 2179, 2111, 2194,  2166, 1813, 1557, 2452, 2705, 1559, 2674, 1882, 1590, 2806, 1618, 2676],
            [2006, 1619, 2678, 1141, 1683, 2680, 2276, 1744, 2735, 2288, 1806, 744,  2291, 1818, 1700, 2295, 1829, 2616, 2303, 2124, 2854, 2305, 2309, 2293],
            [773, 2310, 1385, 2306, 2325, 1116, 2321, 2893, 1401, 2348, 1197, 1542,  2399, 1422, 1817, 2181, 2259, 1257, 1617, 1809, 2244, 2300, 2794, 739],
            [1511, 2463, 2701, 2868, 2702, 2894, 2987, 1243, 2424, 3011, 1477, 2324, 2356, 2425, 981, 1101, 2161, 1250, 2202, 835, 2457, 1404, 1352, 2465],
            [1521, 2296, 1380, 1572, 2339, 1622, 2261, 2341, 2279, 2401, 2207, 2751, 1408, 1610, 873, 904, 2116, 1831, 832, 2113, 2486, 2115, 2280, 1811],
            [726, 2456, 2802, 1836, 786, 1834, 1884, 2731, 2195, 2224, 2285, 2416, 2922, 2426, 1821, 2396, 1454, 2613, 2258, 2264, 2753, 2406, 2693, 2772],
            [2407, 2976, 2411, 2721, 1333, 2035, 2197, 1835, 2437, 1786, 2445, 2011, 2447, 2200, 2448, 2450, 2981, 3171, 3172, 2175, 1871, 2798, 2805, 2807],
            [2820, 1204, 2823, 2386, 2856, 2420, 2859, 2882, 2919, 2173, 3111, 2216,   3137, 2468, 2451, 3138, 2810, 2212, 3139, 3177, 2446, 2204, 3141, 3178],
            [2724, 2704, 3179, 2775, 1854, 1128, 2206, 2153, 1561, 1759, 1787, 1420, 3123, 3117, 2217, 3154, 3163, 782, 3168, 1378, 2326, 3169, 2795, 2865],
            [2994, 2024, 1658, 2755, 2756, 2042, 2243, 2232, 2369, 2844, 2198, 2863, 2249, 2871, 2252, 2881, 3032, 1717, 2832, 927, 1754, 1302, 943, 1840],
            [2916, 1014, 1872, 1023, 1921, 1096, 1961, 1156, 2008, 1174, 2015, 1179, 2043, 1255, 2673, 1429, 2885, 1624, 1633, 1637, 1638, 1714, 1732, 2262]
        ]

        self.pages = len(self.channels)
        self.get_jdata()

        log.d('stop initialization')

    def get_jdata(self):
        threads = []
        bt = time.time()
        with self.lock:
            for page in range(0, self.pages):
                if defines.isCancel():
                    return
                threads.append(defines.MyThread(self.update_epg, page=page))

            for t in threads:
                t.start()
            for t in threads:
                t.join()
        log.d("Loading mailtv in {t} sec".format(t=time.time() - bt))
        return self.jdata

    def _ex_channels(self, page):
        ex = []
        for i, p in enumerate(self.channels):
            if i <= page:
                ex += p
        return ex

    def update_epg(self, page=0):

        mailtv_file = os.path.join(self.epgtv_path, "{0}.gz".format(page))
        valid_date = os.path.exists(fs_str(mailtv_file)) and \
            datetime.date.today() == datetime.date.fromtimestamp(os.path.getmtime(fs_str(mailtv_file)))
        if not valid_date:
            dtm = uni(time.strftime('%Y-%m-%d'))

            url = 'https://tv.mail.ru/ajax/index/'

            _params = {"region_id": 70,
                       "channel_type": "all",
                       "appearance": "list",
                       "period": "all",
                       "date": dtm,
                       "ex": self._ex_channels(page)
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
                # for sch in r.json()['schedule']:
                    # print(sch['channel']['name'].encode('utf8'))
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

    def get_epg_by_id(self, chid, epg_offset=None):
        if chid is None:  # or chid not in self.availableChannels["availableChannelsIds"]:
            return
        ctime = datetime.datetime.now()
        offset = round((ctime - datetime.datetime.utcnow()).total_seconds() / 3600) if epg_offset is None else epg_offset
        bt = None
        ep = None
        for p in itervalues(self.get_jdata()):
            for sch in p['schedule']:
                if sch['channel']['id'] == chid:
                    for evt in sch['event']:

                        bt = map(int, evt['start'].split(':'))
                        bt = datetime.datetime.fromordinal(
                            (ctime.date().toordinal())) + datetime.timedelta(hours=bt[0], minutes=bt[1]) + datetime.timedelta(hours=-3 + offset)
                        if ep is not None:
                            ep['etime'] = time.mktime(bt.timetuple())
                        ep = {}

                        ep['btime'] = time.mktime(bt.timetuple())
                        ep['name'] = evt['name']
                        ep['event_id'] = evt['id']

                        yield ep

    def get_event_info(self, event_id):
        info = {}
        url = 'https://tv.mail.ru/ajax/event/'
        _params = {"region_id": 70,
                   "id": event_id
                   }
        r = defines.request(url, method='post', params=_params, session=self.sess,
                            headers={'Referer': 'https://tv.mail.ru/'})

        if r.ok:
            j = r.json()
            info['desc'] = _tag_re.sub('', j['tv_event']['descr'])
            info['screens'] = [j['tv_event']['sm_image_url']]
            return info

    def get_id_by_name(self, name):
        names = [name.lower()]
        names.extend(CHANNEL_INFO.get(names[0], {}).get("aliases", []))
        for p in itervalues(self.get_jdata()):
            for sch in p['schedule']:
                if sch['channel']['name'].lower() in names:
                    return sch['channel']['id']

    def get_logo_by_id(self, chid):
        if chid is None:  # or chid not in self.availableChannels["availableChannelsIds"]:
            return ''
        for p in itervalues(self.get_jdata()):
            for sch in p['schedule']:
                if sch['channel']['id'] == chid:
                    if 'pic_url' in sch['channel']:
                        return sch['channel']['pic_url']
        return ''


if __name__ == '__main__':
    pass

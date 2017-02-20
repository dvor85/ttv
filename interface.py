# -*- coding: utf-8 -*-

from UserDict import UserDict
import utils
import defines
import xmltv
import re
import logger

fmt = utils.fmt
log = logger.Logger(__name__)
_re_url_match = re.compile('^(?:https?|ftps?|file|[A-z])://')


class Channel(UserDict):

    def __init__(self, data={}):
        self.data = {}
        self.data['type'] = 'channel'
        self.data['cat'] = __name__
        self.data['mode'] = "PID"
        self.data.update(data)

    def get_url(self):
        return self.data.get('url')

    def get_mode(self):
        return self.data.get('mode')

    def get_logo(self):
        if 'logo' in self.data:
            if not _re_url_match.search(self.data['logo']):
                return utils.utf(fmt('http://{0}/uploads/{1}', defines.SITE_MIRROR, self.data['logo']))
            else:
                return utils.utf(self.data['logo'])
        return fmt("{addon_path}/logo/{name}.png", addon_path=utils.utf(defines.ADDON_PATH), name=utils.utf(self.get_name()))

    def get_id(self):
        return utils.utf(fmt("{0}", self.data.get('id')))

    def get_name(self):
        return utils.utf(self.data.get('name'))

    def get_screenshots(self):
        pass

    def get_epg(self):
        """
        epg=[{name, btime, etime},]
        """
        xmltv_epg = xmltv.XMLTV._instance
        if not self.data.get('epg') and xmltv_epg is not None:
            self.data['epg'] = []
            for ep in xmltv_epg.get_epg_by_name(self.get_name()):
                self.data['epg'].append(ep)

        return self.data.get('epg')

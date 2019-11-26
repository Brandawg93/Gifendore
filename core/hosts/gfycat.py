import constants
import logging
from .base import BaseHost
from core.exceptions import InvalidURLError
from gfycat.client import GfycatClient

logger = logging.getLogger("gifendore")


class GfycatHost(BaseHost):
    def __init__(self, inbox_item):
        super().__init__('gfycat', inbox_item, regex=r'http(?:s*)://(?:.*)gfycat.com/([0-9A-Za-z]+)')

    async def get_details(self, url):
        self.vid_url = self.get_preview()
        try:
            self.name = self.regex.findall(url)[0]
        except IndexError:
            raise InvalidURLError('gfycat url not found')
        if self.name is None:
            raise InvalidURLError('gfycat url not found')
        try:
            if self.vid_url is None:
                client = GfycatClient(constants.GFYCAT_CLIENT_ID, constants.GFYCAT_CLIENT_SECRET)
                query = client.query_gfy(self.name)
                if 'mp4Url' in query['gfyItem']:
                    self.vid_url = query['gfyItem']['mp4Url']
                elif 'gifUrl' in query['gfyItem']:
                    self.gif_url = query['gfyItem']['gifUrl']
                else:
                    raise InvalidURLError('gfycat url not found')
            return self.get_info()
        except:
            raise InvalidURLError('gfycat url not found')

import constants
import logging
import re
import requests
from core.exceptions import InvalidURLError
from .base import BaseHost

logger = logging.getLogger("gifendore")


class ImgurHost(BaseHost):
    def __init__(self, inbox_item):
        super().__init__('imgur', inbox_item, regex=r'http(?:s*)://(?:i|m)\.imgur\.com/(.*?)\.')

    async def get_details(self, url):
        self.vid_url = self.get_preview()
        if 'gallery' in url:
            self.regex = re.compile(r'http(?:s*)://imgur\.com/gallery/(.*)', re.I)
        elif '.imgur' not in url:
            self.regex = re.compile(r'http(?:s*)://imgur\.com/(.*)\.(?:.*)', re.I)
        try:
            self.name = self.regex.findall(url)[0]
        except IndexError:
            raise InvalidURLError('Imgur url not found')
        if self.name is None:
            raise InvalidURLError('Imgur url not found')
        if self.vid_url is None:
            headers = {'Authorization': 'Client-ID {}'.format(constants.IMGUR_CLIENT_ID)}
            endpoint = 'album/{}/images'.format(self.name) if 'gallery' in url else 'image/{}'.format(self.name)
            imgur_response = requests.get('https://api.imgur.com/3/{}'.format(endpoint), headers=headers)
            imgur_response.raise_for_status()
            imgur_json = imgur_response.json()
            data = imgur_json['data']
            if isinstance(data, list):
                data = data[0]
            if 'mp4' in data:
                self.vid_url = data['mp4']
            elif 'link' in data:
                self.gif_url = data['link']
            else:
                raise InvalidURLError('Imgur url not found')

        return self.get_info()

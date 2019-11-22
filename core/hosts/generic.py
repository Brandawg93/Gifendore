from .base import BaseHost
from core.exceptions import InvalidHostError


class GenericHost(BaseHost):
    def __init__(self, inbox_item):
        super().__init__(None, inbox_item)

    async def get_details(self):
        self.vid_url = self.get_preview()
        url = self.inbox_item.submission.url
        self.name = url.replace('/', '_')
        if self.vid_url is None:
            if '.mp4' in url:
                self.vid_url = url
            elif '.gif' in url:
                self.gif_url = url
            else:
                raise InvalidHostError('Host is not valid')

        return self.get_info()

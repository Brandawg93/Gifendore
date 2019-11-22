import requests
import constants
import logging
from .imgur import ImgurHost
from .reddit import IRedditHost, VRedditHost
from .gfycat import GfycatHost
from .youtube import YoutubeHost
from .streamable import StreamableHost
from .generic import GenericHost
from core.media import Video, Gif
from PIL import Image
from base64 import b64encode
from io import BytesIO
from core.exceptions import UploadError

logger = logging.getLogger("gifendore")


async def _get_img_from_url(url):
    response = requests.get(url)
    return Image.open(BytesIO(response.content))


async def upload_image(image):
    """upload the frame to imgur"""
    buffer = BytesIO()
    image.save(buffer, **image.info, format='PNG')
    headers = {"Authorization": "Client-ID {}".format(constants.IMGUR_CLIENT_ID)}
    response = requests.post(
        'https://api.imgur.com/3/image',
        headers=headers,
        data={
            'image': b64encode(buffer.getvalue()),
            'type': 'base64'
        }
    )
    response.raise_for_status()
    json = response.json()
    if 'data' in json and 'link' in json['data']:
        url = json['data']['link']
        logger.info('image uploaded to {}'.format(url))
        return url
    else:
        raise UploadError('Imgur upload failed')


class Host:
    def __init__(self, inbox_item):
        self.inbox_item = inbox_item
        self.vid_url = None
        self.gif_url = None
        self.img_url = None
        self.name = None

    async def set_media_details(self):
        url = self.inbox_item.submission.url
        imgur_host = ImgurHost(self.inbox_item)
        i_reddit_host = IRedditHost(self.inbox_item)
        v_reddit_host = VRedditHost(self.inbox_item)
        gfycat_host = GfycatHost(self.inbox_item)
        youtube_host = YoutubeHost(self.inbox_item)
        streamable_host = StreamableHost(self.inbox_item)

        if imgur_host.is_host(url):
            details = await imgur_host.get_details(url)
        elif i_reddit_host.is_host(url):
            details = await i_reddit_host.get_details(url)
        elif v_reddit_host.is_host(url):
            details = await v_reddit_host.get_details(url)
        elif gfycat_host.is_host(url):
            details = await gfycat_host.get_details(url)
        elif youtube_host.is_host(url):
            details = await youtube_host.get_details(url)
        elif streamable_host.is_host(url):
            details = await streamable_host.get_details(url)
        else:
            generic_host = GenericHost(self.inbox_item)
            details = await generic_host.get_details()

        self.vid_url, self.gif_url, self.img_url, self.name = details

    async def get_image(self, seconds):
        image = None
        if self.vid_url:
            video = Video(self.vid_url)
            image, seconds = await video.extract_frame(seconds=seconds)
        elif self.gif_url:
            gif = Gif(self.gif_url)
            image, seconds = await gif.extract_frame(seconds=seconds)
        elif self.img_url:
            image = await _get_img_from_url(self.img_url)
        return image, seconds

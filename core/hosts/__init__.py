"""Host functionality package."""
import requests
import constants
import logging
import time
import os
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
from requests_toolbelt import MultipartEncoder
from decorators import timeout, retry

logger = logging.getLogger("gifendore")


async def get_img_from_url(url):
    """Return a PIL image from a url."""
    response = requests.get(url)
    return Image.open(BytesIO(response.content))


async def upload_image(image):
    """Upload the frame to imgur."""
    buffer = BytesIO()
    image.save(buffer, **image.info, format='JPEG', optimize=True)
    headers = {"Authorization": "Client-ID {}".format(constants.IMGUR_CLIENT_ID)}
    response = requests.post(
        'https://api.imgur.com/3/upload',
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
    raise UploadError('Imgur upload failed')


@retry(3)
async def upload_video(file, inbox_item):
    """Upload the video to gfycat."""
    submission = inbox_item.item.submission

    # get token first
    body = {
        "grant_type": "client_credentials",
        "client_id": constants.GFYCAT_CLIENT_ID,
        "client_secret": constants.GFYCAT_CLIENT_SECRET,
    }
    token = requests.post("https://api.gfycat.com/v1/oauth/token", json=body, timeout=3).json()

    # create gfycat
    auth_headers = {
        "Authorization": token["token_type"] + ' ' + token["access_token"]
    }
    info = {
        "title": submission.title,
        "tags": ["gifendore", "reddit"],
        "nsfw": 1 if submission.over_18 else 0
    }
    create = requests.post("https://api.gfycat.com/v1/gfycats", json=info, headers=auth_headers)
    gfyid = create.json().get("gfyname")

    # upload file to filedrop
    if gfyid:
        upload_url = "https://filedrop.gfycat.com"
        files = {
            "key": gfyid,
            "file": (gfyid, open(file, "rb"), "video/mp4")
        }

        m = MultipartEncoder(fields=files)
        headers = {
            'Content-Type': m.content_type,
            'User-Agent': "Gifendore gifs"
        }
        try:
            res = requests.post(upload_url, data=m, headers=headers)
            res.raise_for_status()
        except Exception as e:
            os.remove(file)
            raise e

        ticket = await _check_upload_status(gfyid, auth_headers)
        task = ticket.get("task")
        if task == "error":
            return None

        url = "https://gfycat.com/{}".format(ticket.get("gfyname"))
        logger.info('video uploaded to {}'.format(url))
        return url


@timeout(120)
async def _check_upload_status(gfyid, headers):
    """Check to see if gfycat has uploaded."""
    ticket_url = "https://api.gfycat.com/v1/gfycats/fetch/status/" + gfyid
    ticket = None

    while ticket is None or (ticket["task"] == "encoding" or ticket['task'] == 'NotFoundo'):
        time.sleep(constants.SLEEP_TIME)
        r = requests.get(ticket_url, headers=headers)
        ticket = r.json()

    return ticket


class Host:
    def __init__(self, inbox_item):
        """Host class to details from an inbox item."""
        self.inbox_item = inbox_item
        self.vid_url = None
        self.gif_url = None
        self.img_url = None
        self.name = None

    async def set_media_details(self):
        """Set the media details of the inbox item."""
        url = self.inbox_item.submission.url
        imgur_host = ImgurHost(self.inbox_item)
        i_reddit_host = IRedditHost(self.inbox_item)
        v_reddit_host = VRedditHost(self.inbox_item)
        gfycat_host = GfycatHost(self.inbox_item)
        youtube_host = YoutubeHost(self.inbox_item)
        streamable_host = StreamableHost(self.inbox_item)
        generic_host = GenericHost(self.inbox_item)

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
            details = await generic_host.get_details(url)

        self.vid_url, self.gif_url, self.img_url, self.name = details

    async def get_image(self, seconds):
        """Get last frame from media."""
        image = None
        if self.vid_url:
            video = Video(self.vid_url)
            image, seconds = await video.extract_frame(seconds=seconds)
        elif self.gif_url:
            gif = Gif(self.gif_url)
            image, seconds = await gif.extract_frame(seconds=seconds)
        elif self.img_url:
            image = await get_img_from_url(self.img_url)
        return image, seconds

    async def get_slo_mo(self, speed):
        """Get slow mo version of media."""
        video = None
        if self.vid_url:
            video = Video(self.vid_url)
            video, speed = await video.slow_mo(speed=speed)
        elif self.gif_url:
            logger.error("not implemented")
        elif self.img_url:
            logger.error("not implemented")
        return video, speed

    async def get_freeze(self):
        """Get freeze version of media."""
        video = None
        if self.vid_url:
            video = Video(self.vid_url)
            video = await video.freeze()
        elif self.gif_url:
            logger.error("not implemented")
        elif self.img_url:
            logger.error("not implemented")
        return video

    async def get_reverse(self):
        """Get reverse of media."""
        video = None
        if self.vid_url:
            video = Video(self.vid_url)
            video = await video.reverse()
        elif self.gif_url:
            logger.error("not implemented")
        elif self.img_url:
            logger.error("not implemented")
        return video

    async def get_section(self, section):
        """Get section of media."""
        video = None
        start, end = section
        if self.vid_url:
            video = Video(self.vid_url)
            video = await video.section(start, end)
        elif self.gif_url:
            logger.error("not implemented")
        elif self.img_url:
            logger.error("not implemented")
        return video

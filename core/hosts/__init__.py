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
from core.media.base import add_watermark
from core.exceptions import VideoNotFoundError
from PIL import Image
from base64 import b64encode
from io import BytesIO
from core.exceptions import UploadError
from requests_toolbelt import MultipartEncoder
from decorators import timeout, retry

logger = logging.getLogger("gifendore")


def get_img_from_url(url):
    """Return a PIL image from a url."""
    response = requests.get(url)
    image = Image.open(BytesIO(response.content))
    add_watermark(image)
    return image


def upload_image(image):
    """Upload the frame to imgur."""
    buffer = BytesIO()
    image.save(buffer, **image.info, format='PNG')
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
def upload_video(file, inbox_item):
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

        res = requests.post(upload_url, data=m, headers=headers)
        res.raise_for_status()
        os.remove(file)

        ticket = _check_upload_status(gfyid, auth_headers)
        task = ticket.get("task")
        if task == "error":
            return None

        url = "https://gfycat.com/{}".format(ticket.get("gfyname"))
        logger.info('video uploaded to {}'.format(url))
        return url


@timeout(120)
def _check_upload_status(gfyid, headers):
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

    def set_media_details(self):
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
            details = imgur_host.get_details(url)
        elif i_reddit_host.is_host(url):
            details = i_reddit_host.get_details(url)
        elif v_reddit_host.is_host(url):
            details = v_reddit_host.get_details(url)
        elif gfycat_host.is_host(url):
            details = gfycat_host.get_details(url)
        elif youtube_host.is_host(url):
            details = youtube_host.get_details(url)
        elif streamable_host.is_host(url):
            details = streamable_host.get_details(url)
        else:
            details = generic_host.get_details(url)

        self.vid_url, self.gif_url, self.img_url, self.name = details

    def get_image(self, seconds):
        """Get last frame from media."""
        image = None
        if not seconds:
            seconds = 0.0
        if self.vid_url:
            video = Video(self.vid_url)
            image, seconds = video.extract_frame(seconds=abs(float(seconds)))
        elif self.gif_url:
            gif = Gif(self.gif_url)
            image, seconds = gif.extract_frame(seconds=abs(float(seconds)))
        elif self.img_url:
            image = get_img_from_url(self.img_url)
        return image, seconds

    def get_slo_mo(self, speed):
        """Get slow mo version of media."""
        if not speed:
            speed = 2.0
        if self.vid_url:
            video = Video(self.vid_url)
            return video.slow_mo(speed=abs(float(speed)))
        else:
            raise VideoNotFoundError

    def get_freeze(self):
        """Get freeze version of media."""
        if self.vid_url:
            video = Video(self.vid_url)
            return video.freeze()
        else:
            raise VideoNotFoundError

    def get_reverse(self):
        """Get reverse of media."""
        if self.vid_url:
            video = Video(self.vid_url)
            return video.reverse()
        else:
            raise VideoNotFoundError

    def get_section(self, section):
        """Get section of media."""
        start, end = section
        if self.vid_url:
            video = Video(self.vid_url)
            return video.section(start, end)
        else:
            raise VideoNotFoundError

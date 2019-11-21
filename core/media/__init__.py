from .gif import Gif
from .video import Video
from PIL import Image
import requests
from io import BytesIO


async def get_img_from_url(url):
    response = requests.get(url)
    return Image.open(BytesIO(response.content))

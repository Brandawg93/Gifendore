import logging
from .gif import Gif
from .video import Video
from PIL import Image
import requests
from io import BytesIO

logger = logging.getLogger("gifendore")

def is_black(img):
	try:
		threshold = 1.0
		r, g, b = img.resize((1, 1), Image.ANTIALIAS).getpixel((0, 0))
		average = (r + g + b) / 3
		logger.debug("average color is {}.".format(average))
		if average <= threshold:
			logger.info('Image too dark.')
		return average <= threshold
	except:
		return False

async def get_img_from_url(url):
	response = requests.get(url)
	return Image.open(BytesIO(response.content))

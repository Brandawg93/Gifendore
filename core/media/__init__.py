from .gif import Gif
from .video import Video
from PIL import Image

def is_black(img):
	try:
		threshold = 0
		r, g, b = img.resize((1, 1), Image.ANTIALIAS).getpixel((0, 0))
		average = (r + g + b) / 3
		if average <= threshold:
			print('Image too dark.')
		return average <= threshold
	except:
		return False

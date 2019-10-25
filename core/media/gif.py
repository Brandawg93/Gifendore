import logging
import requests
from PIL import Image
from .base import BaseMedia
from io import BytesIO

logger = logging.getLogger("gifendore")


class Gif(BaseMedia):
	def __init__(self, url):
		response = requests.get(url)
		response.raise_for_status()
		self.bytes = BytesIO(response.content)

	async def extract_frame(self, seconds=0.0):
		"""extract frame from gif"""
		image = None
		while image is None:
			seconds_text = 'at {} second(s) '.format(seconds) if seconds > 0 else ''
			logger.info('extracting frame {}from gif'.format(seconds_text))
			frame = Image.open(self.bytes)
			if frame.format != 'GIF':
				return frame

			palette = frame.copy().getpalette()
			last = None
			if seconds == 0 or 'duration' not in frame.info:
				try:
					while True:
						last = frame.copy()
						frame.seek(frame.tell() + 1)
				except EOFError:
					pass
			else:
				fps = 1000 / frame.info['duration']
				frame_num = int(seconds * fps)
				range_num = 1 if frame.n_frames - frame_num < 1 else frame.n_frames - frame_num
				try:
					for x in range(range_num):
						last = frame.copy()
						frame.seek(frame.tell() + 1)
				except EOFError:
					pass

			last.putpalette(palette)
			image = Image.new("RGB", last.size)
			image.paste(last)
			if self.is_black(image):
				image = None
				seconds += 1
		return image, seconds

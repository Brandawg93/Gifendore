import logging
import requests
from PIL import Image
from .base import is_black
from io import BytesIO

logger = logging.getLogger("gifendore")


class Gif:
	def __init__(self, url):
		response = requests.get(url)
		response.raise_for_status()
		self.bytes = BytesIO(response.content)

	async def extract_frame(self, seconds=0.0):
		"""Extract frame from gif."""
		image = None
		while image is None:
			seconds_text = 'at {} second(s) '.format(seconds) if seconds > 0 else ''
			logger.info('extracting frame {}from gif'.format(seconds_text))
			frame = Image.open(self.bytes)
			if frame.format != 'GIF':
				return frame, 0.0

			palette = frame.copy().getpalette()
			last = None
			try:
				if seconds == 0 or 'duration' not in frame.info:
					while True:
						frame.seek(frame.tell() + 1)
				else:
					fps = 1000 / frame.info['duration']
					frame_num = int(seconds * fps)
					range_num = 1 if frame.n_frames - frame_num < 1 else frame.n_frames - frame_num
					for _ in range(range_num):
						frame.seek(frame.tell() + 1)
					last = frame.copy()
			except EOFError:
				last = frame.copy()

			last.putpalette(palette)
			image = Image.new("RGB", last.size)
			image.paste(last)
			if is_black(image):
				image = None
				seconds += 1
		return image, seconds

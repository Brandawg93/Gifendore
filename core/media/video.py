import logging
import requests
from os import remove
from PIL import Image
from cv2 import VideoCapture, CAP_PROP_POS_FRAMES, CAP_PROP_FRAME_COUNT, CAP_PROP_FPS

from core.exceptions import ParseError

logger = logging.getLogger("gifendore")


class Video:
	def __init__(self, name):
		self.name = name + ".mp4"

	async def download_from_url(self, url):
		logger.info('downloading {}'.format(url))
		response = requests.get(url)
		response.raise_for_status()

		with open(self.name, 'wb') as file:
			[file.write(chunk) for chunk in response.iter_content(chunk_size=255) if chunk]

	async def extract_frame(self, seconds=0.0):
		"""extract frame from vid"""
		seconds_text = 'at {} second(s) '.format(seconds) if seconds > 0 else ''
		logger.info('extracting frame {}from video'.format(seconds_text))

		cap = VideoCapture(self.name)
		fps = cap.get(CAP_PROP_FPS)
		ret = False
		tries = 0
		img = None
		while not ret and tries < 3:
			frame_num = int(seconds * fps) + tries
			if frame_num > cap.get(CAP_PROP_FRAME_COUNT):
				frame_num = cap.get(CAP_PROP_FRAME_COUNT)

			cap.set(CAP_PROP_POS_FRAMES, cap.get(CAP_PROP_FRAME_COUNT) - frame_num)
			ret, img = cap.read()
			tries += 1
		cap.release()
		if not ret or img is None:
			raise ParseError('Video parse failed')

		image = Image.fromarray(img)

		b, g, r = image.split()
		image = Image.merge("RGB", (r, g, b))
		return image

	def remove(self):
		try:
			remove(self.name)
		except OSError:
			pass

import logging
from PIL import Image
from cv2 import VideoCapture, CAP_PROP_POS_FRAMES, CAP_PROP_FRAME_COUNT, CAP_PROP_FPS
from core.exceptions import ParseError
from .base import is_black

logger = logging.getLogger("gifendore")


class Video:
	def __init__(self, url):
		self.cap = VideoCapture(url)

	async def extract_frame(self, seconds=0.0):
		"""extract frame from vid"""
		image = None
		while image is None:
			seconds_text = 'at {} second(s) '.format(seconds) if seconds > 0 else ''
			logger.info('extracting frame {}from video'.format(seconds_text))

			fps = self.cap.get(CAP_PROP_FPS)
			ret = False
			tries = 0
			frame = None
			while not ret and tries < 3:
				frame_num = int(seconds * fps) + tries
				if frame_num > self.cap.get(CAP_PROP_FRAME_COUNT):
					frame_num = self.cap.get(CAP_PROP_FRAME_COUNT)

				self.cap.set(CAP_PROP_POS_FRAMES, self.cap.get(CAP_PROP_FRAME_COUNT) - frame_num)
				ret, frame = self.cap.read()
				tries += 1
			if not ret or frame is None:
				raise ParseError('Video parse failed')

			image = Image.fromarray(frame)

			b, g, r = image.split()
			image = Image.merge("RGB", (r, g, b))
			if is_black(image):
				image = None
				seconds += 1
		self.cap.release()
		return image, seconds

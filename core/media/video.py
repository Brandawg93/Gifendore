import logging
import cv2
import numpy as np
from PIL import Image
from core.exceptions import ParseError
from .base import is_black, add_watermark

logger = logging.getLogger("gifendore")
FILENAME = 'temp.mp4'


def _add_watermark_to_frame(frame):
	"""Add watermark to numpy frame."""
	pill = Image.fromarray(frame)
	add_watermark(pill)
	return np.array(pill)


class Video:
	def __init__(self, url):
		"""Video manipulation class."""
		self.cap = cv2.VideoCapture(url)
		self.fps = self.cap.get(cv2.CAP_PROP_FPS)
		self.size = (int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))

	async def extract_frame(self, seconds=0.0):
		"""Extract frame from vid."""
		image = None
		while image is None:
			seconds_text = 'at {} second(s) '.format(seconds) if seconds > 0 else ''
			logger.info('extracting frame {}from video'.format(seconds_text))

			ret = False
			tries = 0
			frame = None
			while not ret and tries < 3:
				frame_num = int(seconds * self.fps) + tries
				if frame_num > self.cap.get(cv2.CAP_PROP_FRAME_COUNT):
					frame_num = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)

				self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.cap.get(cv2.CAP_PROP_FRAME_COUNT) - frame_num)
				ret, frame = self.cap.read()
				tries += 1
			if not ret or frame is None:
				raise ParseError('Video parse failed')

			frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
			image = Image.fromarray(frame)

			if is_black(image):
				image = None
				seconds += 1
		self.cap.release()
		add_watermark(image)
		return image, seconds

	async def section(self, start, end):
		"""Get a section of the vid."""
		start_text = 'start' if start == '\\*' else start
		end_text = 'end' if end == '\\*' else end
		logger.info('getting section of vid from {} to {} seconds'.format(start_text, end_text))
		fourcc = cv2.VideoWriter_fourcc(*'mp4v')
		out = cv2.VideoWriter(FILENAME, fourcc, self.fps, self.size)
		if start == '\\*':
			start = 0
		if end == "\\*":
			end = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
		end_frame = int(end) * self.fps
		start_frame = int(start) * self.fps
		self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
		while self.cap.isOpened() and self.cap.get(cv2.CAP_PROP_POS_FRAMES) < end_frame:
			ret, frame = self.cap.read()
			if ret:
				# write the frame
				out.write(_add_watermark_to_frame(frame))
			else:
				break
		out.release()
		self.cap.release()
		return FILENAME

	async def slow_mo(self, speed=2.0):
		"""Slow down vid."""
		speed = 2.0 if speed == 0 else speed
		logger.info('slow mo-ing vid by {} times'.format(speed))
		fourcc = cv2.VideoWriter_fourcc(*'mp4v')
		out = cv2.VideoWriter(FILENAME, fourcc, self.fps/speed, self.size)
		while self.cap.isOpened():
			ret, frame = self.cap.read()
			if ret:
				# write the flipped frame
				out.write(_add_watermark_to_frame(frame))
			else:
				break
		out.release()
		self.cap.release()
		return FILENAME, speed

	async def freeze(self):
		"""Freeze the gif at the end."""
		logger.info('freezing gif at end')
		fourcc = cv2.VideoWriter_fourcc(*'mp4v')
		out = cv2.VideoWriter(FILENAME, fourcc, self.fps, self.size)
		last_frame = None
		while self.cap.isOpened():
			ret, frame = self.cap.read()
			if ret:
				# write the flipped frame
				img = _add_watermark_to_frame(frame)
				out.write(img)
				last_frame = img
			else:
				break
		for _ in range(int(self.fps) * 2):
			out.write(last_frame)
		out.release()
		self.cap.release()
		return FILENAME

	async def reverse(self):
		"""Reverse vid."""
		logger.info('reversing vid')
		fourcc = cv2.VideoWriter_fourcc(*'mp4v')
		out = cv2.VideoWriter(FILENAME, fourcc, self.fps, self.size)
		frames = []
		while self.cap.isOpened():
			ret, frame = self.cap.read()
			if ret:
				frames.append(_add_watermark_to_frame(frame))
			else:
				break
		for frame in reversed(frames):
			out.write(frame)
		out.release()
		self.cap.release()
		return FILENAME

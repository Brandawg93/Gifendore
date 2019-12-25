import logging
import os
from PIL import Image
import cv2
from core.exceptions import ParseError
from .base import is_black

logger = logging.getLogger("gifendore")


class Video:
	def __init__(self, url):
		self.cap = cv2.VideoCapture(url)

	async def extract_frame(self, seconds=0.0):
		"""extract frame from vid"""
		image = None
		while image is None:
			seconds_text = 'at {} second(s) '.format(seconds) if seconds > 0 else ''
			logger.info('extracting frame {}from video'.format(seconds_text))

			fps = self.cap.get(cv2.CAP_PROP_FPS)
			ret = False
			tries = 0
			frame = None
			while not ret and tries < 3:
				frame_num = int(seconds * fps) + tries
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
		return image, seconds

	async def section(self, start, end):
		"""get a section of the vid"""
		start_text = 'start' if start == '\\*' else start
		end_text = 'end' if end == '\\*' else end
		logger.info('getting section of vid from {} to {} seconds'.format(start_text, end_text))
		fps = self.cap.get(cv2.CAP_PROP_FPS)
		size = (int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
		fourcc = cv2.VideoWriter_fourcc(*'mp4v')
		out = cv2.VideoWriter('temp.mp4', fourcc, fps, size)
		if start == '\\*':
			start = 0
		if end == "\\*":
			end = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
		end_frame = int(end) * fps
		start_frame = int(start) * fps
		self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
		while self.cap.isOpened() and self.cap.get(cv2.CAP_PROP_POS_FRAMES) < end_frame:
			ret, frame = self.cap.read()
			if ret:
				# write the frame
				out.write(frame)
			else:
				break
		out.release()
		self.cap.release()
		with open('temp.mp4', "rb") as vid:
			data = vid.read()
			os.remove('temp.mp4')
		return data

	async def slow_mo(self, speed=2.0):
		"""slow down vid"""
		speed = 2.0 if speed == 0 else speed
		logger.info('slow mo-ing vid by {} times'.format(speed))
		fps = self.cap.get(cv2.CAP_PROP_FPS)
		size = (int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
		fourcc = cv2.VideoWriter_fourcc(*'mp4v')
		out = cv2.VideoWriter('temp.mp4', fourcc, fps/speed, size)
		while self.cap.isOpened():
			ret, frame = self.cap.read()
			if ret:
				# write the flipped frame
				out.write(frame)
			else:
				break
		out.release()
		self.cap.release()
		with open('temp.mp4', "rb") as vid:
			data = vid.read()
			os.remove('temp.mp4')
		return data, speed

	async def reverse(self):
		"""reverse vid"""
		logger.info('reversing vid')
		fps = self.cap.get(cv2.CAP_PROP_FPS)
		size = (int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
		fourcc = cv2.VideoWriter_fourcc(*'mp4v')
		out = cv2.VideoWriter('temp.mp4', fourcc, fps, size)
		frames = []
		while self.cap.isOpened():
			ret, frame = self.cap.read()
			if ret:
				frames.append(frame)
			else:
				break
		for frame in reversed(frames):
			out.write(frame)
		out.release()
		self.cap.release()
		with open('temp.mp4', "rb") as vid:
			data = vid.read()
			os.remove('temp.mp4')
		return data

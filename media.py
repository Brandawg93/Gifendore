import requests
from PIL import Image
from cv2 import VideoCapture, CAP_PROP_POS_FRAMES, CAP_PROP_FRAME_COUNT, CAP_PROP_FPS
from os import remove
from exceptions import ParseError
from io import BytesIO

class Video:
	def __init__(self, name, inbox_item):
		self.inbox_item = inbox_item
		self.name = name

	async def download_from_url(self, url):
		print('downloading {}'.format(url))
		response = requests.get(url)
		response.raise_for_status()

		with open('{}.mp4'.format(self.name),'wb') as file:
			[file.write(chunk) for chunk in response.iter_content(chunk_size=255) if chunk]

	async def extract_frame(self, seconds=0.0):
		'''extract frame from vid'''
		#seconds = inbox_item.check_for_args()
		seconds_text = 'at {} second(s) '.format(seconds) if seconds > 0 else ''
		print('extracting frame {}from video'.format(seconds_text))
		self.name += ".mp4"

		cap = VideoCapture(self.name)
		fps = cap.get(CAP_PROP_FPS)
		ret = False
		tries = 0
		while not ret and tries < 3:
			frame_num = int(seconds * fps) + tries
			if frame_num > cap.get(CAP_PROP_FRAME_COUNT):
				frame_num = cap.get(CAP_PROP_FRAME_COUNT)

			cap.set(CAP_PROP_POS_FRAMES, cap.get(CAP_PROP_FRAME_COUNT) - frame_num)
			ret, img = cap.read()
			tries += 1
		cap.release()
		if not ret:
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

class Gif:
	def __init__(self, inbox_item):
		self.inbox_item = inbox_item
		self.bytes = None

	async def download_from_url(self, url):
		response = requests.get(url)
		response.raise_for_status()
		self.bytes = BytesIO(response.content)

	async def extract_frame(self, seconds=0.0):
		'''extract frame from gif'''
		seconds_text = 'at {} second(s) '.format(seconds) if seconds > 0 else ''
		print('extracting frame {}from gif'.format(seconds_text))
		frame = Image.open(self.bytes)
		if frame.format != 'GIF':
			return await uploadToImgur(self.bytes, self.inbox_item)

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
		return last

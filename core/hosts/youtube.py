import constants
from .base import BaseHost
from core.exceptions import InvalidURLError

class YoutubeHost(BaseHost):
	def __init__(self):
		super().__init__('youtube', regex=r'https://www\.youtube\.com/watch(?:/)*\?v=(.+)')

	async def get_details(self, url):
		try:
			self.name = self.regex.findall(url)[0]
		except IndexError:
			raise InvalidURLError('youtube url not found')
		if self.name is None:
			raise InvalidURLError('youtube url not found')
		self.img_url = "https://img.youtube.com/vi/{}/maxresdefault.jpg".format(self.name)
		return self.get_info()

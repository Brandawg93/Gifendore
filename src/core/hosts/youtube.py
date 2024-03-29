from .base import BaseHost
from core.exceptions import InvalidURLError


class YoutubeHost(BaseHost):
	def __init__(self, inbox_item):
		"""Youtube host class."""
		super().__init__('youtu', inbox_item, regex=r'(https://(?:.)*\.youtube\.com/watch(?:/)*\?v=(.+))|(https://youtu\.be/(.+))')

	def get_details(self, url):
		"""Get details from youtube url."""
		try:
			lst = self.regex.findall(url)[0]
			self.name = [x for x in lst if x != '' and 'https://' not in x][0]
		except IndexError:
			raise InvalidURLError('youtube url not found')
		if self.name is None or self.name == '':
			raise InvalidURLError('youtube url not found')
		self.img_url = "https://img.youtube.com/vi/{}/maxresdefault.jpg".format(self.name)
		return self.get_info()

import requests
import constants
from core.exceptions import InvalidURLError
from .base import BaseHost


class StreamableHost(BaseHost):
	def __init__(self, inbox_item):
		"""Streamable host class."""
		super().__init__('streamable', inbox_item, regex=r'http(?:s*)://streamable.com/(.*)')

	async def get_details(self, url):
		"""Get details from streamable url."""
		self.vid_url = self.get_preview()
		try:
			self.name = self.regex.findall(url)[0]
		except IndexError:
			raise InvalidURLError('streamable url not found')
		if self.name is None:
			raise InvalidURLError('streamable url not found')
		if self.vid_url is None:
			auth = (constants.EMAIL, constants.REDDIT_PASSWORD)
			response = requests.get('https://api.streamable.com/videos/{}'.format(self.name), auth=auth)
			response.raise_for_status()
			json = response.json()
			if 'files' in json and 'mp4' in json['files']:
				self.vid_url = 'https:' + json['files']['mp4']['url']
			else:
				raise InvalidURLError('streamable url not found')

		return self.get_info()

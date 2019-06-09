from .base import BaseHost
from core.exceptions import InvalidHostError

class GenericHost(BaseHost):
	def __init__(self, inbox_item):
		super().__init__(None)
		self.inbox_item = inbox_item

	async def get_details(self):
		url = self.inbox_item.submission.url
		if '.mp4' in url:
			self.vid_url = url
		elif '.gif' in url:
			self.gif_url = url
		else:
			raise InvalidHostError('Host is not valid')

		self.name = url.replace('/', '_')
		return self.get_info()
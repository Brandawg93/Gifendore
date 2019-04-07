import constants
from .base import BaseHost
from core.exceptions import InvalidURLError
from gfycat.client import GfycatClient

class GfycatHost(BaseHost):
	def __init__(self):
		super().__init__('gfycat', regex=r'http(s*)://(.*)gfycat.com/([0-9A-Za-z]+)')

	async def get_details(self, url):
		self.name = self.regex.findall(url)[0][2]
		if self.name is None:
			raise InvalidURLError('gfycat url not found')
		client = GfycatClient(constants.GFYCAT_CLIENT_ID, constants.GFYCAT_CLIENT_SECRET)
		query = client.query_gfy(self.name)
		if 'mp4Url' in query['gfyItem']:
			self.vid_url = query['gfyItem']['mp4Url']
		elif 'gifUrl' in query['gfyItem']:
			self.gif_url = query['gfyItem']['gifUrl']
		else:
			raise InvalidURLError('gfycat url not found')

		return self.get_info()

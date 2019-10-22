from .imgur import ImgurHost
from .reddit import IRedditHost, VRedditHost
from .gfycat import GfycatHost
from .youtube import YoutubeHost
from .streamable import StreamableHost
from .generic import GenericHost

class Host:
	def __init__(self, inbox_item):
		self.inbox_item = inbox_item

	async def get_media_details(self, url):
		imgur_host = ImgurHost()
		i_reddit_host = IRedditHost(self.inbox_item)
		v_reddit_host = VRedditHost(self.inbox_item)
		gfycat_host = GfycatHost()
		youtube_host = YoutubeHost()
		streamable_host = StreamableHost()

		if imgur_host.is_host(url):
			return await imgur_host.get_details(url)
		elif i_reddit_host.is_host(url):
			return await i_reddit_host.get_details(url)
		elif v_reddit_host.is_host(url):
			return await v_reddit_host.get_details(url)
		elif gfycat_host.is_host(url):
			return await gfycat_host.get_details(url)
		elif youtube_host.is_host(url):
			return await youtube_host.get_details(url)
		elif streamable_host.is_host(url):
			return await streamable_host.get_details(url)
		else:
			generic_host = GenericHost(self.inbox_item)
			return await generic_host.get_details()

	async def get_details(self, url):
		raise NotImplementedError('get_details has not been implemented')

	async def upload_image(self, image):
		return await ImgurHost().upload_image(image)

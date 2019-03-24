import re, constants, requests
from exceptions import InvalidHostError, InvalidURLError
from gfycat.client import GfycatClient

class Host:
	def __init__(self):
		pass

	async def get_media_details(self, url, inbox_item):
		imgur_host = ImgurHost()
		i_reddit_host = IRedditHost()
		v_reddit_host = VRedditHost()
		gfycat_host = GfycatHost()

		if imgur_host.is_host(url):
			return await imgur_host.get_details(url, inbox_item)
		elif i_reddit_host.is_host(url):
			return await i_reddit_host.get_details(url, inbox_item)
		elif v_reddit_host.is_host(url):
			return await v_reddit_host.get_details(url, inbox_item)
		elif gfycat_host.is_host(url):
			return await gfycat_host.get_details(url, inbox_item)
		else:
			raise InvalidHostError('Host is not valid')

	async def get_details(self, url, inbox_item):
		raise NotImplementedError('get_details has not been implemented')

class ParentHost:
	def __init__(self, url_text, regex=r''):
		self.url_text = url_text
		self.regex = re.compile(regex, re.I)
		self.vid_url = None
		self.vid_name = None
		self.gif_url = None
		self.gif_name = None

	def is_host(self, url):
		return self.url_text in url

	def get_info(self):
		return self.vid_url, self.vid_name, self.gif_url, self. gif_name

class ImgurHost(ParentHost):
	def __init__(self):
		super().__init__('i.imgur', regex=r'http(s*)://i\.imgur\.com/(.*?)\.')

	async def get_details(self, url, inbox_item):
		id = self.regex.findall(url)[0][1]
		headers = {'Authorization': 'Client-ID {}'.format(constants.IMGUR_CLIENT_ID)}
		imgur_response = requests.get('https://api.imgur.com/3/image/{}'.format(id), headers=headers)
		imgur_response.raise_for_status()
		imgur_json = imgur_response.json()
		if 'mp4' in imgur_json['data']:
			self.vid_url = imgur_json['data']['mp4']
			self.vid_name = id
		elif 'link' in imgur_json['data']:
			self.gif_url = imgur_json['data']['link']
		else:
			raise InvalidURLError('Imgur url not found')

		return self.get_info()

class IRedditHost(ParentHost):
	def __init__(self):
		super().__init__('i.redd.it')

	async def get_details(self, url, inbox_item):
		self.gif_url = url
		return self.get_info()

class VRedditHost(ParentHost):
	def __init__(self):
		super().__init__('v.redd.it')

	async def get_details(self, url, inbox_item):
		submission = inbox_item.submission
		self.vid_name = submission.id
		media = None
		if hasattr(submission, 'secure_media'):
			media = submission.secure_media
		cross = None
		if hasattr(submission, 'crosspost_parent_list'):
			cross = submission.crosspost_parent_list
		if media is not None and 'reddit_video' in media and 'fallback_url' in media['reddit_video']:
			self.vid_url = media['reddit_video']['fallback_url']
		elif cross is not None and len(cross) > 0 and 'secure_media' in cross[0] and 'reddit_video' in cross[0]['secure_media'] and 'fallback_url' in cross[0]['secure_media']['reddit_video']:
			self.vid_url = cross[0]['secure_media']['reddit_video']['fallback_url']
		else:
			raise InvalidURLError('vReddit url not found')

		return self.get_info()

class GfycatHost(ParentHost):
	def __init__(self):
		super().__init__('gfycat', regex=r'http(s*)://(.*)gfycat.com/([0-9A-Za-z]+)')

	async def get_details(self, url, inbox_item):
		self.gfy_name = self.regex.findall(url)[0][2]
		self.vid_name = self.gfy_name
		client = GfycatClient(constants.GFYCAT_CLIENT_ID, constants.GFYCAT_CLIENT_SECRET)
		query = client.query_gfy(self.gfy_name)
		if 'mp4Url' in query['gfyItem']:
			self.vid_url = query['gfyItem']['mp4Url']
		elif 'gifUrl' in query['gfyItem']:
			self.gif_url = query['gfyItem']['gifUrl']
		else:
			raise InvalidURLError('gfycat url not found')

		return self.get_info()

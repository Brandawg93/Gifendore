import re, constants, requests
from base64 import b64encode
from PIL import Image
from io import BytesIO
from exceptions import InvalidHostError, InvalidURLError, UploadError
from gfycat.client import GfycatClient

class Host:
	def __init__(self, inbox_item):
		self.inbox_item = inbox_item

	async def get_media_details(self, url):
		imgur_host = ImgurHost()
		i_reddit_host = IRedditHost()
		v_reddit_host = VRedditHost(self.inbox_item)
		gfycat_host = GfycatHost()
		streamable_host = StreamableHost()

		if imgur_host.is_host(url):
			return await imgur_host.get_details(url)
		elif i_reddit_host.is_host(url):
			return await i_reddit_host.get_details(url)
		elif v_reddit_host.is_host(url):
			return await v_reddit_host.get_details(url)
		elif gfycat_host.is_host(url):
			return await gfycat_host.get_details(url)
		elif streamable_host.is_host(url):
			return await streamable_host.get_details(url)
		else:
			raise InvalidHostError('Host is not valid')

	async def get_details(self, url):
		raise NotImplementedError('get_details has not been implemented')

	async def upload_image(self, image):
		return await ImgurHost().upload_image(image)

class BaseHost:
	def __init__(self, url_text, regex=r''):
		self.url_text = url_text
		self.regex = re.compile(regex, re.I)
		self.vid_url = None
		self.gif_url = None
		self.name = None

	def is_host(self, url):
		return self.url_text in url

	def get_info(self):
		return self.vid_url, self.gif_url, self.name

class ImgurHost(BaseHost):
	def __init__(self):
		super().__init__('i.imgur', regex=r'http(s*)://i\.imgur\.com/(.*?)\.')

	async def get_details(self, url):
		self.name = self.regex.findall(url)[0][1]
		if self.name is None:
			raise InvalidURLError('Imgur url not found')
		headers = {'Authorization': 'Client-ID {}'.format(constants.IMGUR_CLIENT_ID)}
		imgur_response = requests.get('https://api.imgur.com/3/image/{}'.format(self.name), headers=headers)
		imgur_response.raise_for_status()
		imgur_json = imgur_response.json()
		if 'mp4' in imgur_json['data']:
			self.vid_url = imgur_json['data']['mp4']
		elif 'link' in imgur_json['data']:
			self.gif_url = imgur_json['data']['link']
		else:
			raise InvalidURLError('Imgur url not found')

		return self.get_info()

	async def upload_image(self, image):
		'''upload the frame to imgur'''
		buffer = BytesIO()
		image.save(buffer, **image.info, format='PNG')
		headers = {"Authorization": "Client-ID {}".format(constants.IMGUR_CLIENT_ID)}
		response = requests.post(
			'https://api.imgur.com/3/image',
			headers=headers,
			data={
				'image': b64encode(buffer.getvalue()),
				'type': 'base64'
			}
		)
		response.raise_for_status()
		json = response.json()
		if 'data' in json and 'link' in json['data']:
			url = json['data']['link']
			print('image uploaded to {}'.format(url))
			return url
		else:
			raise UploadError('Imgur upload failed')

class IRedditHost(BaseHost):
	def __init__(self):
		super().__init__('i.redd.it')

	async def get_details(self, url):
		self.gif_url = url
		return self.get_info()

class VRedditHost(BaseHost):
	def __init__(self, inbox_item):
		super().__init__('v.redd.it')
		self.inbox_item = inbox_item

	async def get_details(self, url):
		submission = self.inbox_item.submission
		self.name = submission.id
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

class StreamableHost(BaseHost):
	def __init__(self):
		super().__init__('streamable', regex=r'http(s*)://streamable.com/(.*)')

	async def get_details(self, url):
		self.name = self.regex.findall(url)[0][1]
		if self.name is None:
			raise InvalidURLError('streamable url not found')
		auth=(constants.EMAIL, constants.REDDIT_PASSWORD)
		response = requests.get('https://api.streamable.com/videos/{}'.format(self.name), auth=auth)
		json = response.json()
		if 'files' in json and 'mp4' in json['files']:
			self.vid_url = 'https:' + json['files']['mp4']['url']
		else:
			raise InvalidURLError('streamable url not found')

		return self.get_info()

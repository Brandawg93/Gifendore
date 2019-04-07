import requests, constants
from core.exceptions import InvalidURLError, UploadError
from .base import BaseHost
from base64 import b64encode
from io import BytesIO

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

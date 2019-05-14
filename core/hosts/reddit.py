from core.exceptions import InvalidURLError
from .base import BaseHost

class IRedditHost(BaseHost):
	def __init__(self, inbox_item):
		super().__init__('i.redd.it')
		self.inbox_item = inbox_item

	async def get_details(self, url):
		self.gif_url = url
		submission = self.inbox_item.submission
		self.name = submission.id
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

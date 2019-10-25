import logging
from .base import BaseMemory
from core.config import config

logger = logging.getLogger("gifendore")


class UserMemory(BaseMemory):
	def __init__(self):
		super().__init__()

	def add(self, user, post, comment):
		try:
			# ex: expire time in seconds
			# nx: only set if key does not exist
			self.r.set('sub:{}-user:{}-post:{}'.format(config.subreddit, user, post), comment, ex=None, nx=False)
			return True
		except Exception as e:
			logger.debug(e)
			return False

	def remove(self, user, post):
		try:
			self.r.delete('sub:{}-user:{}-post:{}'.format(config.subreddit, user, post))
			return True
		except Exception as e:
			logger.debug(e)
			return False

	def get(self, user, post):
		try:
			return self.r.get('sub:{}-user:{}-post:{}'.format(config.subreddit, user, post))
		except Exception as e:
			logger.debug(e)
			return None

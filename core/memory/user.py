from .base import BaseMemory
from core.config import config


class UserMemory(BaseMemory):
	def __init__(self):
		"""Initialize user memory."""
		super().__init__()

	def add(self, user, post, comment):
		return self.redis_add('sub:{}-user:{}-post:{}'.format(config.subreddit, user, post), comment)

	def remove(self, user, post):
		return self.redis_delete('sub:{}-user:{}-post:{}'.format(config.subreddit, user, post))

	def get(self, user, post):
		return self.redis_get('sub:{}-user:{}-post:{}'.format(config.subreddit, user, post))

from .base import BaseMemory

class UserMemory(BaseMemory):
	def __init__(self, config):
		super().__init__()
		self.subreddit = config.subreddit

	def add(self, user, post, comment):
		try:
			#ex: expire time in seconds
			#nx: only set if key does not exist
			self.r.set('sub:{}-user:{}-post:{}'.format(self.subreddit, user, post), comment, ex=None, nx=False)
			return True
		except:
			return False

	def remove(self, user, post):
		try:
			self.r.delete('sub:{}-user:{}-post:{}'.format(self.subreddit, user, post))
			return True
		except:
			return False

	def get(self, user, post):
		try:
			return self.r.get('sub:{}-user:{}-post:{}'.format(self.subreddit, user, post))
		except:
			return None

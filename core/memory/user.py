from .base import BaseMemory

class UserMemory(BaseMemory):
	def __init__(self):
		super().__init__()

	def add(self, user, post, comment):
		try:
			#ex: expire time in seconds
			#nx: only set if key does not exist
			self.r.set('user:{}-post:{}'.format(user, post), comment, ex=None, nx=False)
			return True
		except:
			return False

	def remove(self, user, post):
		try:
			self.r.delete('user:{}-post:{}'.format(user, post))
			return True
		except:
			return False

	def get(self, user, post):
		try:
			return self.r.get('user:{}-post:{}'.format(user, post))
		except:
			return None

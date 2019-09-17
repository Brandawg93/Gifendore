import redis, constants

class Memory:
	def __init__(self):
		self.r = redis.from_url(constants.REDIS_URL, decode_responses=True)

	def add(self, id, url, seconds=0):
		try:
			self.r.set('{}-{}'.format(id, seconds), url)
			return True
		except:
			return False

	def remove(self, id, seconds=0):
		try:
			self.r.delete('{}-{}'.format(id, seconds))
			return True
		except:
			return False

	def get(self, id, seconds=0):
		try:
			return self.r.get('{}-{}'.format(id, seconds))
		except:
			return None

	def exists(self, id, seconds=0):
		try:
			return self.r.exists('{}-{}'.format(id, seconds))
		except:
			return False

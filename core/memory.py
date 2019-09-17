import redis, constants

class Memory:
	def __init__(self):
#		self.memory = {}
		self.r = redis.from_url(constants.REDIS_URL)

	def add(self, id, url, seconds=0):
		try:
			if not self.exists(id, seconds=seconds):
#				self.memory['{}-{}'.format(id, seconds)] = url
				self.r.set('{}-{}'.format(id, seconds), url)
				return True
			else:
				return False
		except:
			return False

	def remove(self, id, seconds=0):
		try:
#			del self.memory['{}-{}'.format(id, seconds)]
			self.r.delete('{}-{}'.format(id, seconds))
			return True
		except:
			return False

	def get(self, id, seconds=0):
		try:
			if self.exists(id, seconds=seconds):
#				return self.memory['{}-{}'.format(id, seconds)]
				return self.r.get('{}-{}'.format(id, seconds))
			else:
				return None
		except:
			return None

	def exists(self, id, seconds=0):
		try:
#			return '{}-{}'.format(id, seconds) in self.memory.keys()
			return self.r.exists('{}-{}'.format(id, seconds))
		except:
			return False

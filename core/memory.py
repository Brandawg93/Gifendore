class Memory:
	def __init__(self):
		self.memory = {}

	def add(self, id, url, seconds=0):
		try:
			if not self.exists(id, seconds=seconds):
				self.memory['{}-{}'.format(id, seconds)] = url
				return True
			else:
				return False
		except:
			return False

	def remove(self, id, seconds=0):
		try:
			del self.memory['{}-{}'.format(id, seconds)]
			return True
		except:
			return False

	def get(self, id, seconds=0):
		try:
			if self.exists(id, seconds=seconds):
				return self.memory['{}-{}'.format(id, seconds)]
			else:
				return None
		except:
			return None

	def exists(self, id, seconds=0):
		try:
			return '{}-{}'.format(id, seconds) in self.memory.keys()
		except:
			return False
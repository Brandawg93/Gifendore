import redis, constants

class BaseMemory:
	def __init__(self):
		self.r = redis.from_url(constants.REDIS_URL, decode_responses=True)
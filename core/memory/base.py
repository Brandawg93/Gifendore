import constants
import redis
import logging
from decorators import timeout

logger = logging.getLogger("gifendore")


class BaseMemory:
    def __init__(self):
        self.r = redis.from_url(constants.REDIS_URL, decode_responses=True)

    @timeout(3)
    def redis_add(self, key, value):
        try:
            # ex: expire time in seconds
            # nx: only set if key does not exist
            self.r.set(key, value, ex=None, nx=False)
            return True
        except Exception as e:
            logger.warning(e)
            return False

    @timeout(3)
    def redis_delete(self, key):
        try:
            self.r.delete(key)
            return True
        except Exception as e:
            logger.warning(e)
            return False

    @timeout(3)
    def redis_get(self, key):
        try:
            return self.r.get(key)
        except Exception as e:
            logger.warning(e)
            return None

import logging
from .base import BaseMemory

logger = logging.getLogger("gifendore")


class PostMemory(BaseMemory):
    def __init__(self):
        super().__init__()

    def add(self, post_id, url, seconds=0):
        try:
            # ex: expire time in seconds
            # nx: only set if key does not exist
            self.r.set('{}-{}'.format(post_id, seconds), url, ex=None, nx=False)
            return True
        except Exception as e:
            logger.debug(e)
            return False

    def remove(self, post_id, seconds=0):
        try:
            self.r.delete('{}-{}'.format(post_id, seconds))
            return True
        except Exception as e:
            logger.debug(e)
            return False

    def get(self, post_id, seconds=0):
        try:
            return self.r.get('{}-{}'.format(post_id, seconds))
        except Exception as e:
            logger.debug(e)
            return None

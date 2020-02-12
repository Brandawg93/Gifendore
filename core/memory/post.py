from .base import BaseMemory

WEEK = 604800


class PostMemory(BaseMemory):
    def __init__(self):
        """Initialize post memory."""
        super().__init__()

    def add(self, post, url, seconds=0):
        return self.redis_add('{}-{}'.format(post, seconds), url, ex=WEEK)

    def remove(self, post, seconds=0):
        return self.redis_delete('{}-{}'.format(post, seconds))

    def get(self, post, seconds=0):
        return self.redis_get('{}-{}'.format(post, seconds))

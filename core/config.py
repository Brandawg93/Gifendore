import sys

class Config:
	def __init__(self):
		self._is_testing_environ = 'production' not in sys.argv
		self._use_memory = '-M' in sys.argv
		self.subreddit = 'gifendore_testing' if self._is_testing_environ else 'gifendore'

import json, sys

class Config:
	def __init__(self):
		with open('core/config.json') as f:
			self.data = json.load(f)

		self._is_testing_environ = 'production' not in sys.argv
		self._use_memory = '-M' in sys.argv
		self.subreddit = 'gifendore_testing' if self._is_testing_environ else 'gifendore'

	def get_banned_subs(self):
		return self.data['manually_included_banned_subs']

import sys, praw, constants
from praw.models import CommunityList

class Config:
	def __init__(self):
		self._is_testing_environ = 'production' not in sys.argv
		self._use_memory = '-M' in sys.argv
		self.subreddit = 'gifendore_testing' if self._is_testing_environ else 'gifendore'
		if self._use_memory:
			print('using memory')
		if self._is_testing_environ:
			print('using testing environment')

		self.r = self._init_reddit()
		self.banned_subs = None

		#check if current subreddit in list of subs in sidebar
		try:
			widgets = self.r.subreddit('gifendore').widgets
			for widget in widgets.sidebar:
				if isinstance(widget, CommunityList) and widget.shortName == 'Subs with Spam Detection':
					self.banned_subs = [x.display_name for x in widget]
		except:
			self.banned_subs = None

	def _init_reddit(self):
		'''initialize the reddit instance'''
		return praw.Reddit(client_id=constants.REDDIT_CLIENT_ID_TESTING if self._is_testing_environ else constants.REDDIT_CLIENT_ID,
			client_secret=constants.REDDIT_CLIENT_SECRET_TESTING if self._is_testing_environ else constants.REDDIT_CLIENT_SECRET,
			password=constants.REDDIT_PASSWORD,
			user_agent='mobile:gifendore:0.1 (by /u/brandawg93)',
			username=constants.REDDIT_USERNAME_TESTING if self._is_testing_environ else constants.REDDIT_USERNAME)

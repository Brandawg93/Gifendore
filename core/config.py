import sys, praw, constants, logging
from praw.models import CommunityList

logger = logging.getLogger("gifendore")

class Config:
	def __init__(self):
		self._is_testing_environ = 'production' not in sys.argv
		self._use_memory = '-M' in sys.argv
		self.subreddit = 'gifendore_testing' if self._is_testing_environ else 'gifendore'

		self.log_level = logging.DEBUG if '-D' in sys.argv else logging.INFO
		self.formatter = logging.Formatter('{}[%(name)s] [%(levelname)s] %(message)s'.format('[%(asctime)s] ' if '-D' in sys.argv else ''))
		self._init_logger()
		if self._use_memory:
			logger.info('using memory')
		if self._is_testing_environ:
			logger.info('using testing environment')

		self.r = self._init_reddit()
		self.moderators = self.get_mods()
		self.banned_subs = self.get_banned_subs()

	def _init_reddit(self):
		'''initialize the reddit instance'''
		try:
			return praw.Reddit(client_id=constants.REDDIT_CLIENT_ID_TESTING if self._is_testing_environ else constants.REDDIT_CLIENT_ID,
				client_secret=constants.REDDIT_CLIENT_SECRET_TESTING if self._is_testing_environ else constants.REDDIT_CLIENT_SECRET,
				password=constants.REDDIT_PASSWORD,
				user_agent='mobile:gifendore:0.1 (by /u/brandawg93)',
				username=constants.REDDIT_USERNAME_TESTING if self._is_testing_environ else constants.REDDIT_USERNAME)
		except:
			return None

	def get_mods(self):
		'''refresh the moderators list'''
		try:
			return self.r.subreddit(self.subreddit).moderator()
		except:
			return None

	def get_banned_subs(self):
		'''check if current subreddit in list of subs in sidebar'''
		try:
			widgets = self.r.subreddit('gifendore').widgets
			for widget in widgets.sidebar:
				if isinstance(widget, CommunityList) and widget.shortName == 'Subs with Spam Detection':
					return [x.display_name for x in widget]
		except:
			return None

	def _init_logger(self):
		'''initialize the logger'''
		ch = logging.StreamHandler(sys.stdout)
		ch.setLevel(self.log_level)
		ch.setFormatter(self.formatter)
		logger.addHandler(ch)
		logger.setLevel(self.log_level)

config = Config()

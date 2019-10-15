import sys, praw, constants, logging
from praw.models import CommunityList

logger = logging.getLogger("gifendore")

class Config:
	def __init__(self):
		self._is_testing_environ = 'production' not in sys.argv
		self._use_memory = '-M' in sys.argv
		self.subreddit = 'gifendore_testing' if self._is_testing_environ else 'gifendore'

		self._init_logger()
		if self._use_memory:
			logger.info('using memory')
		if self._is_testing_environ:
			logger.info('using testing environment')

		self.r = self._init_reddit()
		self.moderators = None
		self.refresh_mods()
		self.banned_subs = None
		self.refresh_banned_subs()

	def _init_reddit(self):
		'''initialize the reddit instance'''
		return praw.Reddit(client_id=constants.REDDIT_CLIENT_ID_TESTING if self._is_testing_environ else constants.REDDIT_CLIENT_ID,
			client_secret=constants.REDDIT_CLIENT_SECRET_TESTING if self._is_testing_environ else constants.REDDIT_CLIENT_SECRET,
			password=constants.REDDIT_PASSWORD,
			user_agent='mobile:gifendore:0.1 (by /u/brandawg93)',
			username=constants.REDDIT_USERNAME_TESTING if self._is_testing_environ else constants.REDDIT_USERNAME)

	def refresh_mods(self):
		'''refresh the moderators list'''
		self.moderators = self.r.subreddit(self.subreddit).moderator()

	def refresh_banned_subs(self):
		'''check if current subreddit in list of subs in sidebar'''
		try:
			widgets = self.r.subreddit('gifendore').widgets
			for widget in widgets.sidebar:
				if isinstance(widget, CommunityList) and widget.shortName == 'Subs with Spam Detection':
					self.banned_subs = [x.display_name for x in widget]
		except:
			self.banned_subs = None

	def _init_logger(self):
		'''initialize the logger'''
		level = logging.DEBUG if '-D' in sys.argv else logging.INFO
		ch = logging.StreamHandler(sys.stdout)
		ch.setLevel(level)
		formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
		ch.setFormatter(formatter)
		logger.addHandler(ch)
		logger.setLevel(level)

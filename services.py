import constants
import logging
from sentry_sdk.integrations.redis import RedisIntegration
from urllib.parse import urlparse
from core.config import config
from pymongo import MongoClient

logger = logging.getLogger("gifendore")

def log_event(name, item, url=None):
	"""Log event to db."""
	try:
		if not config.is_testing_environ:
			if url:
				split_url = urlparse(url)
				url = '{}://{}'.format(split_url.scheme, split_url.netloc)
			
			client = MongoClient(constants.MONGODB_URL)
			db = client.analytics
			db[name].insert_one({
				"user": item.author.name,
				"subreddit": item.submission.subreddit.display_name,
				"host": url
			})			
			logger.debug("sent {} event to db".format(name))
	except Exception as e:
		logger.debug("Could not send to db", exc_info=e)

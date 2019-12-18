import constants
import sentry_sdk
import keen
import logging
from sentry_sdk.integrations.redis import RedisIntegration
from urllib.parse import urlparse
from core.config import config

logger = logging.getLogger("gifendore")
if not config.is_testing_environ:
	sentry_sdk.init(dsn=constants.SENTRY_DSN, environment='production', integrations=[RedisIntegration()])


async def log_event(name, item, url=None):
	"""Log event to keen"""
	try:
		if not config.is_testing_environ:
			if url:
				split_url = urlparse(url)
				url = '{}://{}'.format(split_url.scheme, split_url.netloc)

			keen.add_event(name, {
				"user": item.author.name,
				"subreddit": item.submission.subreddit.display_name,
				"host": url
			})
			logger.debug("sent {} event to keen".format(name))
	except Exception as e:
		logger.debug("Could not send to keen", e)

import pybrake
import constants
import keen
import logging
from urllib.parse import urlparse
from core.config import config

environ = 'development' if config.is_testing_environ else 'production'
ab_logger = pybrake.Notifier(project_key=constants.AIRBRAKE_API_KEY, project_id=constants.AIRBRAKE_PROJECT_ID, environment=environ)
logger = logging.getLogger("gifendore")


async def log_event(name, item, url=None):
	"""Log event to airbrake"""
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

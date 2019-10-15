import keen, airbrake, constants, asyncio
from urllib.parse import urlparse

ab_logger = airbrake.getLogger(api_key=constants.AIRBRAKE_API_KEY, project_id=constants.AIRBRAKE_PROJECT_ID)

async def log_event(name, item, url=None):
	'''Log event to airbrake'''
	try:
		if url is not None:
			split_url = urlparse(url)
			url = '{}://{}'.format(split_url.scheme, split_url.netloc)

		keen.add_event(name, {
			"user": item.author.name,
			"subreddit": item.submission.subreddit.display_name,
			"host": url
		})
	except:
		pass


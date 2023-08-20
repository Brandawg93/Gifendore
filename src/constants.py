from os import environ, path

ENVIRONMENT=environ['ENVIRONMENT']
IMGUR_CLIENT_ID = environ['IMGUR_CLIENT_ID']
IMGUR_CLIENT_SECRET = environ['IMGUR_CLIENT_SECRET']
SENTRY_DSN = environ['SENTRY_DSN']
REDDIT_CLIENT_ID = environ['REDDIT_CLIENT_ID']
REDDIT_CLIENT_SECRET = environ['REDDIT_CLIENT_SECRET']
REDDIT_USERNAME = environ['REDDIT_USERNAME']
REDDIT_PASSWORD = environ['REDDIT_PASSWORD']
EMAIL = environ['EMAIL']
REDIS_URL = environ['REDIS_URL'] if 'REDIS_URL' in environ else None
SUCCESS_TEMPLATE_ID = environ['SUCCESS_TEMPLATE_ID']
ERROR_TEMPLATE_ID = environ['ERROR_TEMPLATE_ID']
MONGODB_URL = environ['MONGODB_URL'] if 'MONGODB_URL' in environ else None

SLEEP_TIME = 5
MARK_READ = True
DIR = path.dirname(path.realpath(__file__)) + '/..'

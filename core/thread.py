import time, logging, sys
from timeloop import Timeloop
from datetime import timedelta
from core.config import config
from services import log_event

logger = logging.getLogger("gifendore")
timer = Timeloop()

CHECK_TIME = 300
DOWNVOTES = -2

class Thread:
	def __init__(self):
		self.set_format()

	def start(self, block=False):
		try:
			timer.start(block)
		except Exception as e:
			logger.exception(e)

	def stop(self):
		try:
			timer.stop()
		except Exception as e:
			logger.exception(e)

	def set_format(self):
		'''change timeloop logger format'''
		tl_logger = logging.getLogger("timeloop")
		for handler in tl_logger.handlers:
			if isinstance(handler, logging.StreamHandler):
				handler.setLevel(config.log_level)
				handler.setFormatter(config.formatter)

@timer.job(interval=timedelta(seconds=CHECK_TIME))
def check_comments():
	'''check last 50 comments for downvotes'''
	logger.debug("checking comments for downvotes")
	try:
		if config is not None:
			for comment in config.r.user.me().comments.new(limit=50):
				if comment.score <= DOWNVOTES:
					logger.info("Found bad comment with score={}".format(comment.score))
#					log_event('downvote_delete', comment)
					comment.delete()
	except Exception as e:
		logger.exception(e)


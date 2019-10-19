import time, logging, sys, asyncio
from timeloop import Timeloop
from datetime import timedelta
from core.config import config
from services import log_event

logger = logging.getLogger("gifendore")
timer = Timeloop()

CHECK_TIME = 300
DOWNVOTES = -2

class Thread:
	'''This class periodically checks comments'''
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

async def _process():
	'''check last 25 comments for downvotes or deleted parents'''
	logger.debug("checking comments for downvotes")
	try:
		if config is not None:
			for comment in config.r.user.me().comments.new(limit=25):
				if comment.score <= DOWNVOTES:
					logger.info("Found bad comment with score={}".format(comment.score))
					comment.delete()
					await log_event('thread_delete', comment)
				elif comment.parent().body.lower() in ['[deleted]', '[removed]']:
					logger.info("Found comment with deleted parent")
					comment.delete()
					await log_event('thread_delete', comment)
	except Exception as e:
		logger.exception(e)

@timer.job(interval=timedelta(seconds=CHECK_TIME))
def check_comments():
	asyncio.run(_process())

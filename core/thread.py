import time, logging, sys
from timeloop import Timeloop
from datetime import timedelta

logger = logging.getLogger("gifendore")
timer = Timeloop()
gbl_config = None

CHECK_TIME = 300
DOWNVOTES = -2

class Thread:
	def __init__(self, config):
		global gbl_config
		gbl_config = config
		self.config = config
		self.set_format()

	def start(self, block=False):
		timer.start(block)

	def stop(self):
		timer.stop()

	def set_format(self):
		'''change timeloop logger format'''
		tl_logger = logging.getLogger("timeloop")
		for handler in tl_logger.handlers:
			if isinstance(handler, logging.StreamHandler):
				handler.setLevel(self.config.log_level)
				handler.setFormatter(self.config.formatter)

@timer.job(interval=timedelta(seconds=CHECK_TIME))
def check_comments():
	'''check last 50 comments for downvotes'''
	logger.debug("checking comments for downvotes")
	try:
		if gbl_config is not None:
			for comment in gbl_config.r.user.me().comments.new(limit=50):
				if comment.score <= DOWNVOTES:
					logger.info("Found bad comment with score={}".format(comment.score))
					comment.delete()
	except Exception as e:
		logger.exception(e)


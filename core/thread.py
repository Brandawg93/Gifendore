import asyncio
import logging
from datetime import timedelta
from praw.models import Submission
from timeloop import Timeloop
from core.config import config
from services import log_event
from prawcore.exceptions import PrawcoreException
from requests.exceptions import HTTPError
from praw.exceptions import APIException, ClientException

logger = logging.getLogger("gifendore")
timer = Timeloop()

CHECK_TIME = 300
DOWNVOTES = -2


class Thread:
    """Class periodically checks comments for downvotes or commands."""

    @staticmethod
    def start(block=False):
        try:
            Thread.set_format()
            timer.start(block)
        except Exception as e:
            logger.exception(e)

    @staticmethod
    def stop():
        try:
            timer.stop()
        except Exception as e:
            logger.exception(e)

    @staticmethod
    def set_format():
        """Change timeloop logger format."""
        tl_logger = logging.getLogger("timeloop")
        for handler in tl_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(config.log_level)
                handler.setFormatter(config.formatter)


async def process():
    """Check last 25 comments for downvotes or deleted parents."""
    logger.debug("checking comments for downvotes")
    try:
        if config:
            for comment in config.r.user.me().comments.new(limit=25):
                parent = comment.parent()
                if comment.score <= DOWNVOTES:
                    logger.info("Found bad comment with score={}".format(comment.score))
                    comment.delete()
                    await log_event('thread_delete', comment)
                elif not isinstance(parent, Submission) and parent.body.lower() in ['[deleted]', '[removed]']:
                    logger.info("Found comment with deleted parent")
                    comment.delete()
                    await log_event('thread_delete', comment)

    except (PrawcoreException, APIException, ClientException, ConnectionError, HTTPError) as e:
        logger.warning(e)

    except Exception as e:
        logger.exception(e)


@timer.job(interval=timedelta(seconds=CHECK_TIME))
def check_comments():
    """Run the process asynchronously on a timer."""
    asyncio.run(process())

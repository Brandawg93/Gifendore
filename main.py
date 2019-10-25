import asyncio
import constants
import logging
import praw
import prawcore
import time
from praw.models import Comment, Submission, Message
from core.config import config
from core.exceptions import Error
from core.hosts import Host
from core.inbox import InboxItem
from core.media import Video, Gif, is_black, get_img_from_url
from core.memory import PostMemory
from core.thread import Thread
from decorators import async_timer
from services import ab_logger, log_event

logger = logging.getLogger("gifendore")


async def check_comment_item(inbox_item):
	"""Parse the comment item to see what action to take"""
	item = inbox_item.item
	# always mark the item as read
	if constants.MARK_READ:
		item.mark_read()
	if config.is_testing_environ and item.author not in config.moderators:
		return
	# do nothing if it isn't a comment or if it was a reply
	if item.was_comment and isinstance(item, Comment) and ('reply' not in item.subject or (
			'u/gifendore' in item.body.lower() and not inbox_item.should_send_pointers())):
		try:
			# check if the user is banned
			if any(config.r.subreddit(config.subreddit).banned(redditor=item.author.name)):
				logger.info('{} is banned from {}'.format(item.author.name, config.subreddit))
				await inbox_item.send_banned_msg()
				return
		except Exception as e:
			logger.exception(e)
			pass
		if item.subreddit.user_is_banned:
			await inbox_item.crosspost_and_pm_user()
		else:
			await process_inbox_item(inbox_item)

	elif item.was_comment and 'reply' in item.subject:
		if inbox_item.should_send_pointers():
			await inbox_item.reply_to_item('(☞ﾟヮﾟ)☞')
			await log_event('easter_egg', item)
		elif 'good bot' in item.body.lower():
			await log_event('good_bot', item)
		elif 'bad bot' in item.body.lower():
			await log_event('bad_bot', item)
		elif 'delete' in item.body.lower():
			try:
				parent = item.parent()
				mention = parent.parent()
				if item.author == mention.author or item.author in config.moderators:
					logger.info('deleting original comment')
					parent.delete()
			except Exception as e:
				logger.exception(e)
			await log_event('delete', item)
		else:
			await log_event('reply', item)


async def check_submission_item(inbox_item):
	"""Parse the submission item to see what action to take"""
	item = inbox_item.item
	if config.is_testing_environ and item.author not in config.moderators:
		return
	if isinstance(item, Submission):
		await process_inbox_item(inbox_item)


@async_timer
async def process_inbox_item(inbox_item):
	"""Process the item depending on the type of media"""
	url = inbox_item.submission.url
	await log_event('mention', inbox_item.item, url=url)
	logger.info('getting submission: {}'.format(inbox_item.submission.shortlink))
	host = Host(inbox_item)
	vid_url, gif_url, img_url, name = await host.get_media_details(url)
	try_mem = config.use_memory and name is not None
	seconds = inbox_item.check_for_args()
	uploaded_url = None
	mem_url = None
	if try_mem:
		memory = PostMemory()
		mem_url = memory.get(name, seconds=seconds)
	if try_mem and mem_url is not None:
		logger.info('{} already exists in memory'.format(name))
		uploaded_url = mem_url
	else:
		image = None
		if vid_url is not None:
			video = Video(name)
			await video.download_from_url(vid_url)
			while image is None:
				image = await video.extract_frame(seconds=seconds)
				if is_black(image):
					image = None
					seconds += 1
			video.remove()

		elif gif_url is not None:
			gif = Gif(inbox_item)
			await gif.download_from_url(gif_url)
			while image is None:
				image = await gif.extract_frame(seconds=seconds)
				if is_black(image):
					image = None
					seconds += 1
		elif img_url is not None:
			image = await get_img_from_url(img_url)
		uploaded_url = await host.upload_image(image)
		if try_mem:
			memory = PostMemory()
			memory.add(name, uploaded_url, seconds=seconds)

	if uploaded_url is not None:
		if seconds > 0:
			await inbox_item.reply_to_item('Here is {} seconds from the end: {}'.format(seconds, uploaded_url))
		elif img_url is not None:
			await inbox_item.reply_to_item('Here is the thumbnail: {}'.format(uploaded_url))
		else:
			await inbox_item.reply_to_item('Here is the last frame: {}'.format(uploaded_url))
	else:
		logger.error('They shouldn\'t have gotten here.')
		# await inbox_item.handle_exception('uploaded_url is None', reply_msg='THERE\'S NO GIF IN HERE!')


def handle_bad_request(bad_requests, inbox_item, e):
	logger.warning('Praw Error: {}'.format(e))
	if inbox_item is not None and inbox_item not in bad_requests:
		bad_requests.append(inbox_item)
	time.sleep(constants.SLEEP_TIME)


async def main():
	"""Loop through mentions"""
	while True:
		bad_requests = []
		inbox_item = None
		try:
			logger.info('polling for new mentions...')
			inbox_stream = config.r.inbox.stream(pause_after=-1)
			subreddit_stream = config.r.subreddit('+'.join([x.title for x in config.r.user.moderator_subreddits()])).stream.submissions(pause_after=-1, skip_existing=True)
			while True:
				for item in bad_requests:
					inbox_item = InboxItem(item)
					if isinstance(item, Comment):
						await check_comment_item(inbox_item)
						bad_requests.remove(item)

					elif isinstance(item, Submission):
						await check_submission_item(inbox_item)
						bad_requests.remove(item)
					else:
						bad_requests.remove(item)

				for item in inbox_stream:
					if item is None:
						break
					elif isinstance(item, Message):
						item.mark_read()
						break
					inbox_item = InboxItem(item)
					await check_comment_item(inbox_item)

				for item in subreddit_stream:
					if item is None:
						break
					inbox_item = InboxItem(item)
					await check_submission_item(inbox_item)

		except KeyboardInterrupt:
			logger.info('Exiting...')
			break

		except prawcore.exceptions.ResponseException as e:
			handle_bad_request(bad_requests, inbox_item, e)

		except prawcore.exceptions.RequestException as e:
			handle_bad_request(bad_requests, inbox_item, e)

		except praw.exceptions.APIException as e:
			handle_bad_request(bad_requests, inbox_item, e)

		except Exception as e:
			if config.is_testing_environ and not isinstance(e, Error):
				raise e
			else:
				try:
					if inbox_item is not None:
						await inbox_item.handle_exception(e)
					else:
						logger.exception(e)
						if not config.is_testing_environ:
							ab_logger.exception(e)
				except Exception as e:
					logger.exception(e)


if __name__ == "__main__":
	timer = Thread()
	timer.start()
	asyncio.run(main())
	timer.stop()

import asyncio
import constants
import logging
import time
from prawcore.exceptions import RequestException, ResponseException, ServerError
from praw.models import Comment, Submission, Message
from core.config import config
from core.exceptions import Error, UploadError
from core.hosts import Host, upload_image, upload_video
from core.inbox import InboxItem
from core.memory import PostMemory, UserMemory
from core.thread import Thread
from decorators import async_timer
from services import log_event

logger = logging.getLogger("gifendore")


async def check_comment_item(inbox_item):
	"""Parse the comment item to see what action to take."""
	item = inbox_item.item
	# always mark the item as read
	if constants.MARK_READ:
		item.mark_read()
	# do nothing if non-moderator calls testing bot
	if config.is_testing_environ and item.author not in config.moderators:
		logger.info("non-moderator called testing bot")
		return
	if item.submission.is_self:
		logger.info("mention was on self post")
		return
	# do nothing if it isn't a comment or if it was a reply
	if ('reply' not in item.subject or ('u/{}'.format(config.subreddit) in item.body.lower() and not inbox_item.should_send_pointers())):
		try:
			# check if the user is banned
			if any(config.r.subreddit(config.subreddit).banned(redditor=item.author.name)):
				logger.info('{} is banned from {}'.format(item.author.name, config.subreddit))
				await inbox_item.send_banned_msg()
				return
		except Exception as e:
			logger.exception(e, inbox_item=inbox_item)
		if item.subreddit.user_is_banned:
			await inbox_item.crosspost_and_pm_user()
		else:
			await process_inbox_item(inbox_item)

	elif 'reply' in item.subject:
		if inbox_item.should_send_pointers():
			await inbox_item.reply_to_item('(☞ﾟヮﾟ)☞')
			await log_event('easter_egg', item)
		elif 'good bot' in item.body.lower():
			await log_event('good_bot', item)
		elif 'bad bot' in item.body.lower():
			await log_event('bad_bot', item)
		else:
			await log_event('reply', item)


async def check_message_item(inbox_item):
	"""Parse the message item to see what action to take."""
	item = inbox_item.item
	# always mark the item as read
	if constants.MARK_READ:
		item.mark_read()
	# do nothing if non-moderator calls testing bot
	if config.is_testing_environ and item.author not in config.moderators:
		logger.info("non-moderator called testing bot")
		return
	command, comment = inbox_item.get_message_command()
	if command == 'delete':
		try:
			author = item.author
			parent = comment.parent()
			if author == parent.author or author in config.moderators or author in parent.subreddit.moderator():
				logger.info('deleting original comment')
				comment.delete()
				await log_event('delete', item)
		except Exception as e:
			logger.exception(e, inbox_item=inbox_item)
	elif command == 'edit':
		parent = comment.parent()
		parent.refresh()
		parent.subject = 'username mention'
		parent.body = inbox_item.item.body
		try:
			author = item.author
			if author == parent.author or author in config.moderators or author in parent.subreddit.moderator():
				inbox_item = InboxItem(parent)
				inbox_item.edit_id = comment.id
				return await process_inbox_item(inbox_item)
		except Exception as e:
			logger.exception(e, inbox_item=inbox_item)


def search_for_comment(mention):
	"""Search for comment by bot."""
	for comment in mention.replies:
		if comment.author.name == config.subreddit:
			return comment

async def check_submission_item(inbox_item):
	"""Parse the submission item to see what action to take."""
	item = inbox_item.item
	# do nothing if non-moderator calls testing bot
	if config.is_testing_environ and item.author not in config.moderators:
		logger.info("non-moderator called testing bot")
		return
	if item.is_self:
		logger.info("post was a self post")
		return
	await process_inbox_item(inbox_item)


@async_timer
async def process_inbox_item(inbox_item):
	"""Process the item depending on the type of media."""
	await log_event('mention', inbox_item.item, url=inbox_item.submission.url)
	logger.info('getting submission: {}'.format(inbox_item.submission.shortlink))
	command = inbox_item.get_command()
	if command == 'help':
		await inbox_item.send_help()
		return
	host = Host(inbox_item)
	await host.set_media_details()
	seconds = inbox_item.get_seconds()
	section = inbox_item.get_section()
	try_mem = config.use_memory and host.name and command is None and section is None
	mem_url = None
	if try_mem:
		memory = PostMemory()
		mem_url = memory.get(host.name, seconds=seconds)
	if try_mem and mem_url:
		logger.info('{} already exists in memory'.format(host.name))
		uploaded_url = mem_url
	else:
		if command == 'slowmo':
			video, seconds = await host.get_slo_mo(seconds)
			uploaded_url = await upload_video(video, inbox_item)
		elif command == 'reverse':
			video = await host.get_reverse()
			uploaded_url = await upload_video(video, inbox_item)
		elif command == 'freeze':
			video = await host.get_freeze()
			uploaded_url = await upload_video(video, inbox_item)
		else:
			if section:
				video = await host.get_section(section)
				uploaded_url = await upload_video(video, inbox_item)
			else:
				image, seconds = await host.get_image(seconds)
				uploaded_url = await upload_image(image)

				if try_mem:
					memory = PostMemory()
					memory.add(host.name, uploaded_url, seconds=seconds)

	if uploaded_url:
		if command == 'slowmo':
			reply_text = 'Here is the gif in slo-mo: {}'.format(uploaded_url)
		elif command == 'reverse':
			reply_text = 'Here is the gif in reverse: {}'.format(uploaded_url)
		elif command == 'freeze':
			reply_text = 'Here is the gif with the end frozen: {}'.format(uploaded_url)
		elif section:
			start, end = section
			start_text = 'start' if start == '\\*' else start
			end_text = 'end' if end == '\\*' else end
			reply_text = 'Here is the gif from {} to {} seconds: {}'.format(start_text, end_text, uploaded_url)
		else:
			if seconds and seconds > 0:
				reply_text = 'Here is {} seconds from the end: {}'.format(seconds, uploaded_url)
			elif host.img_url:
				reply_text = 'Here is the thumbnail: {}'.format(uploaded_url)
			else:
				reply_text = 'Here is the last frame: {}'.format(uploaded_url)
		await inbox_item.reply_to_item(reply_text)
	else:
		raise UploadError


def handle_bad_request(bad_requests, inbox_item, e):
	"""Handle all bad requests."""
	logger.warning(e, inbox_item=inbox_item)
	if inbox_item and inbox_item not in bad_requests:
		bad_requests.append(inbox_item)
	time.sleep(constants.SLEEP_TIME)


async def main():
	"""Loop through mentions."""
	while True:
		bad_requests = []
		inbox_item = None
		try:
			logger.info('polling for new mentions...')
			inbox_stream = config.r.inbox.stream(pause_after=-1)
			mod_subs = [x.title for x in config.r.user.moderator_subreddits()]
			subreddit_stream = config.r.subreddit('+'.join(mod_subs)).stream.submissions(pause_after=-1, skip_existing=True)
			while True:
				inbox_item = None
				for inbox_item in bad_requests:
					if isinstance(inbox_item.item, Comment):
						await check_comment_item(inbox_item)
						bad_requests.remove(inbox_item)

					elif isinstance(inbox_item.item, Submission):
						await check_submission_item(inbox_item)
						bad_requests.remove(inbox_item)
					else:
						bad_requests.remove(inbox_item)

				for item in inbox_stream:
					if item is None:
						break
					inbox_item = InboxItem(item)
					if isinstance(item, Message):
						await check_message_item(inbox_item)
					elif isinstance(item, Comment):
						await check_comment_item(inbox_item)
					else:
						item.mark_read()

				for item in subreddit_stream:
					if item is None:
						break
					inbox_item = InboxItem(item)
					if isinstance(item, Submission):
						await check_submission_item(inbox_item)
					else:
						item.mark_read()

		except KeyboardInterrupt:
			logger.info('Exiting...')
			break

		except (RequestException, ResponseException, ServerError) as e:
			handle_bad_request(bad_requests, inbox_item, e)

		except Exception as e:
			if config.is_testing_environ:
				raise e
			if isinstance(e, Error):
				logger.warning(e, inbox_item=inbox_item)
			else:
				logger.exception(e, inbox_item=inbox_item)


if __name__ == "__main__":
	Thread.start()
	asyncio.run(main())
	Thread.stop()

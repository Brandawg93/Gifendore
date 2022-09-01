import constants
import logging
import time
from prawcore.exceptions import RequestException, ResponseException, ServerError
from praw.exceptions import ClientException
from praw.models import Comment, Submission, Message
from core.config import config
from core.exceptions import Error, UploadError
from core.hosts import Host, upload_image, upload_video
from core.inbox import InboxItem
from core.memory import PostMemory
from core.thread import Thread
from decorators import timer
from services import log_event

logger = logging.getLogger("gifendore")
environment = constants.ENVIRONMENT

def check_comment_item(inbox_item):
	"""Parse the comment item to see what action to take."""
	item = inbox_item.item
	# always mark the item as read
	if constants.MARK_READ:
		item.mark_read()
	# do nothing if non-moderator calls testing bot
	if environment == 'development' and item.author not in config.moderators:
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
				inbox_item.send_banned_msg()
				return
		except Exception as e:
			logger.exception(e, inbox_item=inbox_item)
		if item.subreddit.user_is_banned:
			inbox_item.crosspost_and_pm_user()
		else:
			process_inbox_item(inbox_item)

	elif 'reply' in item.subject:
		if inbox_item.should_send_pointers():
			inbox_item.reply_to_item('(☞ﾟヮﾟ)☞')
			log_event('easter_egg', item)
		elif 'good bot' in item.body.lower():
			log_event('good_bot', item)
		elif 'bad bot' in item.body.lower():
			log_event('bad_bot', item)
			reply = item.parent()
			if reply.parent().author == item.author:
				item.parent().delete()
				logger.info('deleting original comment due to bad bot')
		else:
			log_event('reply', item)


def check_message_item(inbox_item):
	"""Parse the message item to see what action to take."""
	item = inbox_item.item
	# always mark the item as read
	if constants.MARK_READ:
		item.mark_read()
	# do nothing if non-moderator calls testing bot
	if environment == 'development' and item.author not in config.moderators:
		logger.info("non-moderator called testing bot")
		return
	command, comment_id = inbox_item.get_message_command()
	if not command or not comment_id:
		return
	comment = config.r.comment(id=comment_id)
	if command == 'delete':
		try:
			author = item.author
			try:
				parent = comment.parent()
			except ClientException:
				logger.debug("Parent comment was deleted.")
				return
			if author == parent.author or author in config.moderators or author in parent.subreddit.moderator():
				logger.info('deleting original comment')
				comment.delete()
				log_event('delete', item)
		except Exception as e:
			logger.exception(e, inbox_item=inbox_item)
	elif command == 'edit':
		try:
			parent = comment.parent()
		except ClientException:
			logger.debug("Parent comment was deleted.")
			return
		parent.refresh()
		parent.subject = 'username mention'
		parent.body = inbox_item.item.body
		try:
			author = item.author
			if author == parent.author or author in config.moderators or author in parent.subreddit.moderator():
				inbox_item = InboxItem(parent)
				inbox_item.edit_id = comment.id
				return process_inbox_item(inbox_item)
		except Exception as e:
			logger.exception(e, inbox_item=inbox_item)


def search_for_comment(mention):
	"""Search for comment by bot."""
	for comment in mention.replies:
		if comment.author.name == config.subreddit:
			return comment


def check_submission_item(inbox_item):
	"""Parse the submission item to see what action to take."""
	item = inbox_item.item
	# do nothing if non-moderator calls testing bot
	if environment == 'development' and item.author not in config.moderators:
		logger.info("non-moderator called testing bot")
		return
	if item.is_self:
		logger.info("post was a self post")
		return
	process_inbox_item(inbox_item)


@timer
def process_inbox_item(inbox_item):
	"""Process the item depending on the type of media."""
	log_event('mention', inbox_item.item, url=inbox_item.submission.url)
	logger.info('getting submission: {}'.format(inbox_item.submission.shortlink))
	command = inbox_item.get_command()
	if command == 'help':
		inbox_item.send_help()
		return
	host = Host(inbox_item)
	host.set_media_details()
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
			video, seconds = host.get_slo_mo(seconds)
			uploaded_url = upload_video(video, inbox_item)
		elif command == 'reverse':
			video = host.get_reverse()
			uploaded_url = upload_video(video, inbox_item)
		elif command == 'freeze':
			video = host.get_freeze()
			uploaded_url = upload_video(video, inbox_item)
		else:
			if section:
				video = host.get_section(section)
				uploaded_url = upload_video(video, inbox_item)
			else:
				image, seconds = host.get_image(seconds)
				uploaded_url = upload_image(image)

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
			if seconds and float(seconds) > 0:
				reply_text = 'Here is {} seconds from the end: {}'.format(seconds, uploaded_url)
			elif host.img_url:
				reply_text = 'Here is the thumbnail: {}'.format(uploaded_url)
			else:
				reply_text = 'Here is the last frame: {}'.format(uploaded_url)
		inbox_item.reply_to_item(reply_text)
	else:
		raise UploadError


def handle_bad_request(bad_requests, inbox_item, e):
	"""Handle all bad requests."""
	logger.warning(e, inbox_item=inbox_item)
	if inbox_item and inbox_item not in bad_requests:
		bad_requests.append(inbox_item)
	time.sleep(constants.SLEEP_TIME)


def main():
	"""Loop through mentions."""
	while True:
		bad_requests = []
		inbox_item = None
		try:
			logger.info('polling for new mentions...')
			inbox_stream = config.r.inbox.stream(pause_after=-1)
			mod_subs = [x.title for x in config.r.user.me().moderated()]
			subreddit_stream = config.r.subreddit('+'.join(mod_subs)).stream.submissions(pause_after=-1, skip_existing=True)
			while True:
				inbox_item = None
				for inbox_item in bad_requests:
					if isinstance(inbox_item.item, Comment):
						check_comment_item(inbox_item)
						bad_requests.remove(inbox_item)

					elif isinstance(inbox_item.item, Submission):
						check_submission_item(inbox_item)
						bad_requests.remove(inbox_item)
					else:
						bad_requests.remove(inbox_item)

				for item in inbox_stream:
					if item is None:
						break
					inbox_item = InboxItem(item)
					if isinstance(item, Message):
						check_message_item(inbox_item)
					elif isinstance(item, Comment):
						check_comment_item(inbox_item)
					else:
						item.mark_read()

				for item in subreddit_stream:
					if item is None:
						break
					inbox_item = InboxItem(item)
					if isinstance(item, Submission):
						check_submission_item(inbox_item)
					else:
						item.mark_read()

		except (RequestException, ResponseException, ServerError) as e:
			handle_bad_request(bad_requests, inbox_item, e)

		except Exception as e:
			if environment == 'development':
				raise e
			if isinstance(e, Error):
				logger.warning(e, inbox_item=inbox_item)
			else:
				logger.exception(e, inbox_item=inbox_item)


if __name__ == "__main__":
	Thread.start()
	try:
		main()
	except KeyboardInterrupt:
		logger.info('Exiting...')
	Thread.stop()

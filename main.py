import praw, prawcore, sys, asyncio, time, constants, re
from decorators import async_timer
from praw.models import Comment, Submission
from core.inbox import InboxItem
from core.hosts import Host
from core.media import Video, Gif, is_black
from core.config import Config
from core.memory import Memory
from services import logger, log_event

_is_testing_environ = False
_use_memory = False
config = None
memory = None

def set_config():
	global config
	config = Config()

def set_memory():
	global memory
	memory = Memory()

def _init_reddit():
	'''initialize the reddit instance'''
	global _is_testing_environ
	global _use_memory
	_is_testing_environ = 'production' not in sys.argv
	_use_memory = '-M' in sys.argv
	if _use_memory:
		print('using memory')
	if _is_testing_environ:
		print('using testing environment')
	return praw.Reddit(client_id=constants.REDDIT_CLIENT_ID_TESTING if _is_testing_environ else constants.REDDIT_CLIENT_ID,
		client_secret=constants.REDDIT_CLIENT_SECRET_TESTING if _is_testing_environ else constants.REDDIT_CLIENT_SECRET,
		password=constants.REDDIT_PASSWORD,
		user_agent='mobile:gifendore:0.1 (by /u/brandawg93)',
		username=constants.REDDIT_USERNAME_TESTING if _is_testing_environ else constants.REDDIT_USERNAME)

async def check_comment_item(r, item, subreddit):
#	always mark the item as read
	if constants.MARK_READ:
		item.mark_read()
	if _is_testing_environ and item.author not in r.subreddit(subreddit).moderator():
		return
#	do nothing if it isn't a comment or if it was a reply
	if item.was_comment and isinstance(item, Comment) and ('reply' not in item.subject or ('u/gifendore' in item.body and not should_send_pointers(item))):
		inbox_item = InboxItem(item)
		SUBREDDIT = 'gifendore_testing' if _is_testing_environ else 'gifendore'
		try:
#			check if the user is banned
			if any(r.subreddit(SUBREDDIT).banned(redditor=item.author.name)):
				print('{} is banned from {}'.format(item.author.name, SUBREDDIT))
				await inbox_item.send_banned_msg()
				return
		except:
			pass
		if item.subreddit.user_is_banned or item.subreddit in config.get_banned_subs():
			await inbox_item.crosspost_and_pm_user()
		else:
			await process_inbox_item(inbox_item)
	elif item.was_comment and 'reply' in item.subject and should_send_pointers(item):
		item.reply('(☞ﾟヮﾟ)☞')
		if not _is_testing_environ:
			await log_event('easter_egg', item)
	elif item.was_comment and 'reply' in item.subject and 'good bot' in item.body.lower():
		if not _is_testing_environ:
			await log_event('good_bot', item)
	elif item.was_comment and 'reply' in item.subject and 'bad bot' in item.body.lower():
		if not _is_testing_environ:
			await log_event('bad_bot', item)
	elif item.was_comment and 'reply' in item.subject:
		if not _is_testing_environ:
			await log_event('reply', item)

async def check_submission_item(r, item, subreddit):
	if _is_testing_environ and item.author not in r.subreddit(subreddit).moderator():
		return
	if isinstance(item, Submission):
		inbox_item = InboxItem(item)
		await process_inbox_item(inbox_item)

@async_timer
async def process_inbox_item(inbox_item):
	url = inbox_item.submission.url
	if not _is_testing_environ:
		await log_event('mention', inbox_item.item, url=url)
	print('extracting gif from {}'.format(url))

	host = Host(inbox_item)
	vid_url, gif_url, name = await host.get_media_details(url)

	try_mem = _use_memory and memory is not None and name is not None
	seconds = inbox_item.check_for_args()
	if try_mem and memory.exists(name, seconds=seconds):
		uploaded_url = memory.get(name, seconds=seconds)
		print('{} already exists in memory'.format(name))
	else:
		image = None
		if vid_url is not None:
			while image == None:
				video = Video(name, inbox_item)
				await video.download_from_url(vid_url)
				image = await video.extract_frame(seconds=seconds)
				if is_black(image):
					image = None
					seconds += 1
			video.remove()

		elif gif_url is not None:
			while image == None:
				gif = Gif(inbox_item)
				await gif.download_from_url(gif_url)
				image = await gif.extract_frame(seconds=seconds)
				if is_black(image):
					image = None
					seconds += 1

		uploaded_url = await host.upload_image(image)
		if try_mem:
			memory.add(name, uploaded_url, seconds=seconds)

	if uploaded_url is not None:
		if seconds > 0:
			await inbox_item.reply_to_item('Here is {} seconds from the end: {}'.format(seconds, uploaded_url), upvote=True)
		else:
			await inbox_item.reply_to_item('Here is the last frame: {}'.format(uploaded_url), upvote=True)
	else:
		print('Error: They shouldn\'t have gotten here.')
#		await inbox_item.handle_exception('uploaded_url is None', reply_msg='THERE\'S NO GIF IN HERE!')

def should_send_pointers(item):
	return True if re.search('.+points (?:to|for).+gifendore.*', item.body, re.IGNORECASE) else False

async def main():
	while True:
		bad_requests = []
		inbox_item = None
		try:
			set_config()
			r = _init_reddit()
			if _use_memory:
				set_memory()
			SUBREDDIT = 'gifendore_testing' if _is_testing_environ else 'gifendore'
			print('polling for new mentions...')
			inbox_stream = r.inbox.stream(pause_after=-1)
			subreddit_stream = r.subreddit(SUBREDDIT).stream.submissions(pause_after=-1, skip_existing=True)
			while True:
				for item in bad_requests:
					if isinstance(item, Comment):
						await check_comment_item(r, item, SUBREDDIT)
						bad_requests.remove(item)

					elif isinstance(item, Submission):
						await check_submission_item(r, item, SUBREDDIT)
						bad_requests.remove(item)
					else:
						bad_requests.remove(item)

				for item in inbox_stream:
					if item is None:
						break
					await check_comment_item(r, item, SUBREDDIT)

				for item in subreddit_stream:
					if item is None:
						break
					await check_submission_item(r, item, SUBREDDIT)

		except KeyboardInterrupt:
			print('\nExiting...')
			break

		except prawcore.exceptions.ResponseException as e:
			print('ResponseError: {}'.format(e))
			if inbox_item is not None and inbox_item not in bad_requests:
				bad_requests.append(inbox_item)
			time.sleep(constants.SLEEP_TIME)

		except prawcore.exceptions.RequestException as e:
			print('RequestError: {}'.format(e))
			if inbox_item is not None and inbox_item not in bad_requests:
				bad_requests.append(inbox_item)
			time.sleep(constants.SLEEP_TIME)

		except praw.exceptions.APIException as e:
			print('APIError: {}'.format(e))
			if inbox_item is not None and inbox_item not in bad_requests:
				bad_requests.append(inbox_item)
			time.sleep(constants.SLEEP_TIME)

		except Exception as e:
			if _is_testing_environ:
				raise e
			else:
				try:
					if inbox_item is not None:
						await inbox_item.handle_exception(e)
					else:
						print('Error: {}'.format(e))
						logger.exception(e)
				except:
					pass

if __name__ == "__main__":
	asyncio.run(main())

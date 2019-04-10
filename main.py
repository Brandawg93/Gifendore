import praw, prawcore, sys, asyncio, time, constants, re
from decorators import async_timer
from praw.models import Comment, Submission
from core.inbox import InboxItem
from core.hosts import Host
from core.media import Video, Gif
from services import logger, log_event

_is_testing_environ = False

def _init_reddit():
	'''initialize the reddit instance'''
	global _is_testing_environ
	_is_testing_environ = not (len(sys.argv) > 1 and sys.argv[1] == 'production')
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
	if item.was_comment and isinstance(item, Comment) and 'reply' not in item.subject:
		inbox_item = InboxItem(item)
		if item.subreddit.user_is_banned:
			await inbox_item.crosspost_and_pm_user()
		else:
			await process_inbox_item(inbox_item)
	elif item.was_comment and 'reply' in item.subject and should_send_pointers(item):
		item.reply('(☞ﾟヮﾟ)☞')
		await log_event('easter_egg', item)
	elif item.was_comment and 'reply' in item.subject and 'good bot' in item.body.lower():
		await log_event('good_bot', item)
	elif item.was_comment and 'reply' in item.subject and 'bad bot' in item.body.lower():
		await log_event('bad_bot', item)
	elif item.was_comment and 'reply' in item.subject:
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
	await log_event('mention', inbox_item.item, url=url)
	print('extracting gif from {}'.format(url))

	host = Host(inbox_item)
	vid_url, gif_url, name = await host.get_media_details(url)

	image = None
	seconds = inbox_item.check_for_args()
	if vid_url is not None:
		video = Video(name, inbox_item)
		await video.download_from_url(vid_url)
		image = await video.extract_frame(seconds=seconds)
		video.remove()

	elif gif_url is not None:
		gif = Gif(inbox_item)
		await gif.download_from_url(gif_url)
		image = await gif.extract_frame(seconds=seconds)

	uploaded_url = await host.upload_image(image)
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
			r = _init_reddit()
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

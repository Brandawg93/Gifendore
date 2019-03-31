import praw, prawcore, sys, asyncio, airbrake, time, constants
from decorators import async_timer
from praw.models import Comment, Submission
from inbox import InboxItem
from hosts import Host, ImgurHost
from media import Video, Gif

logger = airbrake.getLogger(api_key=constants.AIRBRAKE_API_KEY, project_id=constants.AIRBRAKE_PROJECT_ID)

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

@async_timer
async def process_inbox_item(inbox_item):
	url = inbox_item.submission.url
	print('extracting gif from {}'.format(url))

	host = Host()
	vid_url, gif_url, name = await host.get_media_details(url, inbox_item)

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

	uploaded_url = await ImgurHost().upload_image(image, inbox_item)
	if uploaded_url is not None:
		if seconds > 0:
			await inbox_item.reply_to_item('Here is {} seconds from the end: {}'.format(seconds, uploaded_url))
		else:
			await inbox_item.reply_to_item('Here is the last frame: {}'.format(uploaded_url))
	else:
		print('Error: They shouldn\'t have gotten here.')
#		await inbox_item.handle_exception('uploaded_url is None', reply_msg='THERE\'S NO GIF IN HERE!')

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
					if _is_testing_environ and item.author not in r.subreddit(SUBREDDIT).moderator():
						continue
					if isinstance(item, Comment):
						if constants.MARK_READ:
							item.mark_read()
						if item.was_comment and 'reply' not in item.subject:
							inbox_item = InboxItem(item, item.submission)
							await process_inbox_item(inbox_item)
							bad_requests.remove(item)
					elif isinstance(item, Submission):
						inbox_item = InboxItem(item, item)
						await process_inbox_item(inbox_item)
						bad_requests.remove(item)
					else:
						bad_requests.remove(item)
				for item in inbox_stream:
					if item is None:
						break
#					always mark the item as read
					if constants.MARK_READ:
						item.mark_read()
					if _is_testing_environ and item.author not in r.subreddit(SUBREDDIT).moderator():
						continue
#					do nothing if it isn't a comment or if it was a reply
					if item.was_comment and isinstance(item, Comment) and 'reply' not in item.subject:
						inbox_item = InboxItem(item, item.submission)
						await process_inbox_item(inbox_item)
				for item in subreddit_stream:
					if item is None:
						break
					if _is_testing_environ and item.author not in r.subreddit(SUBREDDIT).moderator():
						continue
					if isinstance(item, Submission):
						inbox_item = InboxItem(item, item)
						await process_inbox_item(inbox_item)

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

import praw, prawcore, requests, sys, asyncio, airbrake, time, constants
from os import remove
from decorators import async_timer
from praw.models import Comment, Submission
from base64 import b64encode
from PIL import Image
from cv2 import VideoCapture, CAP_PROP_POS_FRAMES, CAP_PROP_FRAME_COUNT, CAP_PROP_FPS
from io import BytesIO
from inbox import InboxItem
from hosts import Host
from exceptions import ParseError

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

async def extractFrameFromGif(inGif, inbox_item):
	'''extract frame from gif'''
	seconds = inbox_item.check_for_args()
	seconds_text = 'at {} second(s) '.format(seconds) if seconds > 0 else ''
	print('extracting frame {}from gif'.format(seconds_text))
	frame = Image.open(inGif)
	if frame.format != 'GIF':
		return await uploadToImgur(inGif, inbox_item)

	palette = frame.copy().getpalette()
	last = None
	if seconds == 0 or 'duration' not in frame.info:
		try:
			while True:
				last = frame.copy()
				frame.seek(frame.tell() + 1)
		except EOFError:
			pass
	else:
		fps = 1000 / frame.info['duration']
		frame_num = int(seconds * fps)
		range_num = 1 if frame.n_frames - frame_num < 1 else frame.n_frames - frame_num
		try:
			for x in range(range_num):
				last = frame.copy()
				frame.seek(frame.tell() + 1)
		except EOFError:
			pass

	last.putpalette(palette)
	buffer = BytesIO()
	last.save(buffer, **last.info, format='PNG')
	return await uploadToImgur(buffer, inbox_item)

async def extractFrameFromVid(name, inbox_item):
	'''extract frame from vid'''
	seconds = inbox_item.check_for_args()
	seconds_text = 'at {} second(s) '.format(seconds) if seconds > 0 else ''
	print('extracting frame {}from video'.format(seconds_text))
	name += ".mp4"
	buffer = BytesIO()
	try:
		cap = VideoCapture(name)
		fps = cap.get(CAP_PROP_FPS)
		ret = False
		tries = 0
		while not ret and tries < 3:
			frame_num = int(seconds * fps) + tries
			if frame_num > cap.get(CAP_PROP_FRAME_COUNT):
				frame_num = cap.get(CAP_PROP_FRAME_COUNT)

			cap.set(CAP_PROP_POS_FRAMES, cap.get(CAP_PROP_FRAME_COUNT) - frame_num)
			ret, img = cap.read()
			tries += 1
		cap.release()
		if not ret:
			raise ParseError('Video parse failed')

		image = Image.fromarray(img)

		b, g, r = image.split()
		image = Image.merge("RGB", (r, g, b))
		image.save(buffer, format='PNG')
		remove(name)
		return await uploadToImgur(buffer, inbox_item)

	except Exception as e:
		try:
			remove(name)
		except OSError:
			pass
		raise e

#@async_timer
async def uploadToImgur(bytes, inbox_item):
	'''upload the frame to imgur'''
	headers = {"Authorization": "Client-ID {}".format(constants.IMGUR_CLIENT_ID)}
	upload_url = 'https://api.imgur.com/3/image'
	response = requests.post(
		upload_url,
		headers=headers,
		data={
			'image': b64encode(bytes.getvalue()),
			'type': 'base64'
		}
	)
	response.raise_for_status()

	uploaded_url = None
	json = response.json()
	if 'link' in json['data']:
		uploaded_url = json['data']['link']
	print('image uploaded to {}'.format(uploaded_url))
	return uploaded_url

#@async_timer
async def downloadfile(name, url, inbox_item):
	print('downloading {}'.format(url))
	response = requests.get(url)
	response.raise_for_status()

	with open('{}.mp4'.format(name),'wb') as file:
		[file.write(chunk) for chunk in response.iter_content(chunk_size=255) if chunk]
	return True

@async_timer
async def process_inbox_item(inbox_item):
	url = inbox_item.submission.url
	print('extracting gif from {}'.format(url))

	host = Host()
	vid_url, vid_name, gif_url, gif_name = await host.get_media_details(url, inbox_item)

	uploaded_url = None
	if vid_url is not None:
		if await downloadfile(vid_name, vid_url, inbox_item):
			uploaded_url = await extractFrameFromVid(vid_name, inbox_item)

	elif gif_url is not None:
		gif_response = requests.get(gif_url)
		gif = BytesIO(gif_response.content)
		uploaded_url = await extractFrameFromGif(gif, inbox_item)

	if uploaded_url is not None:
		seconds = inbox_item.check_for_args()
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
			try:
				if inbox_item is not None:
					await inbox_item.handle_exception(e)
				else:
					print('Error: {}'.format(e))
					if not _is_testing_environ:
						logger.exception(e)
			except:
				pass

if __name__ == "__main__":
	asyncio.run(main())

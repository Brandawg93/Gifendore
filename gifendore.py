import praw, prawcore, requests, sys, re, asyncio, airbrake, time
from os import remove, environ
from decorators import async_timer
from praw.models import Comment, Submission
from gfycat.client import GfycatClient
from base64 import b64encode
from PIL import Image
from cv2 import VideoCapture, CAP_PROP_POS_FRAMES, CAP_PROP_FRAME_COUNT
from io import BytesIO
from inbox import InboxItem

IMGUR_CLIENT_ID = environ['IMGUR_CLIENT_ID']
IMGUR_CLIENT_SECRET = environ['IMGUR_CLIENT_SECRET']
GFYCAT_CLIENT_ID = environ['GFYCAT_CLIENT_ID']
GFYCAT_CLIENT_SECRET = environ['GFYCAT_CLIENT_SECRET']
AIRBRAKE_API_KEY = environ['AIRBRAKE_API_KEY']
AIRBRAKE_PROJECT_ID = environ['AIRBRAKE_PROJECT_ID']
REDDIT_CLIENT_ID = environ['REDDIT_CLIENT_ID']
REDDIT_CLIENT_SECRET = environ['REDDIT_CLIENT_SECRET']
REDDIT_CLIENT_ID_TESTING = environ['REDDIT_CLIENT_ID_TESTING']
REDDIT_CLIENT_SECRET_TESTING = environ['REDDIT_CLIENT_SECRET_TESTING']
REDDIT_USERNAME = environ['REDDIT_USERNAME']
REDDIT_USERNAME_TESTING = environ['REDDIT_USERNAME_TESTING']
REDDIT_PASSWORD = environ['REDDIT_PASSWORD']

SLEEP_TIME = 5
MARK_READ = True

logger = airbrake.getLogger(api_key=AIRBRAKE_API_KEY, project_id=AIRBRAKE_PROJECT_ID)

_is_testing_environ = False

def _init_reddit():
	'''initialize the reddit instance'''
	global _is_testing_environ
	_is_testing_environ = not (len(sys.argv) > 1 and sys.argv[1] == 'production')
	if _is_testing_environ:
		print('using testing environment')
	return praw.Reddit(client_id=REDDIT_CLIENT_ID_TESTING if _is_testing_environ else REDDIT_CLIENT_ID,
		client_secret=REDDIT_CLIENT_SECRET_TESTING if _is_testing_environ else REDDIT_CLIENT_SECRET,
		password=REDDIT_PASSWORD,
		user_agent='mobile:gifendore:0.1 (by /u/brandawg93)',
		username=REDDIT_USERNAME_TESTING if _is_testing_environ else REDDIT_USERNAME) # Note: Be sure to change the user-agent to something unique.

async def extractFrameFromGif(inGif, inbox_item):
	'''extract frame from gif'''
	frame_num = inbox_item.check_for_args()
	print('extracting frame {} from gif'.format(frame_num))
	frame = Image.open(inGif)
	if not hasattr(frame, 'n_frames'):
		return None

	palette = frame.copy().getpalette()
	last = None
	if frame_num == 1:
		try:
			while True:
				last = frame.copy()
				frame.seek(frame.tell() + 1)
		except EOFError:
			pass
	else:
		if frame_num > frame.n_frames:
			frame_num = frame.n_frames
		frame.seek(frame.n_frames - frame_num)
		last = frame.copy()

	last.putpalette(palette)
	buffer = BytesIO()
	last.save(buffer, **last.info, format='PNG')
	return uploadToImgur(buffer, inbox_item)

async def extractFrameFromVid(name, inbox_item):
	'''extract frame from vid'''
	frame_num = inbox_item.check_for_args()
	print('extracting frame {} from video'.format(frame_num))
	name += ".mp4"
	buffer = BytesIO()
	try:
		cap = VideoCapture(name)
		ret = False
		tries = 0
		while not ret and tries < 3:
			frame_num += tries
			if frame_num > cap.get(CAP_PROP_FRAME_COUNT):
				frame_num = cap.get(CAP_PROP_FRAME_COUNT)

			cap.set(CAP_PROP_POS_FRAMES, cap.get(CAP_PROP_FRAME_COUNT) - frame_num)
			ret, img = cap.read()
			tries += 1
		cap.release()
		if not ret:
			inbox_item.handle_exception('could not parse mp4', '')
			return None

		image = Image.fromarray(img)

		b, g, r = image.split()
		image = Image.merge("RGB", (r, g, b))
		image.save(buffer, format='PNG')
		remove(name)
		return uploadToImgur(buffer, inbox_item)

	except Exception as e:
		try:
			remove(name)
		except OSError:
			pass
		raise e

def uploadToImgur(bytes, inbox_item):
	'''upload the frame to imgur'''
	headers = {"Authorization": "Client-ID {}".format(IMGUR_CLIENT_ID)}
	upload_url = 'https://api.imgur.com/3/image'
	response = requests.post(
		upload_url,
		headers=headers,
		data={
			'image': b64encode(bytes.getvalue()),
			'type': 'base64'
		}
	)
	if response.status_code == 500:
		inbox_item.handle_exception('imgur is not responding', 'IMGUR IS DOWN!')
		return None

	uploaded_url = None
	json = response.json()
	if 'link' in json['data']:
		uploaded_url = json['data']['link']
	print('image uploaded to {}'.format(uploaded_url))
	return uploaded_url

@async_timer
async def downloadfile(name, url, inbox_item):
	print('downloading {}'.format(url))
	url_content = requests.get(url)
	if url_content.status_code == 500:
		inbox_item.handle_exception('download is not responding', 'HOSTED SITE IS DOWN!')
		return False

	with open('{}.mp4'.format(name),'wb') as file:
		[file.write(chunk) for chunk in url_content.iter_content(chunk_size=255) if chunk]
	return True

async def process_inbox_item(inbox_item):
	submission = inbox_item.submission
	url = submission.url
	print('extracting gif from {}'.format(url))
	gif_url = None
	vid_url = None
	vid_name = None
	if 'i.imgur' in url:
		regex = re.compile(r'http(s*)://i\.imgur\.com/(.*?)\.', re.I)
		id = regex.findall(url)[0][1]
		headers = {'Authorization': 'Client-ID {}'.format(IMGUR_CLIENT_ID)}
		imgur_response = requests.get('https://api.imgur.com/3/image/{}'.format(id), headers=headers)
		if imgur_response.status_code == 500:
			inbox_item.handle_exception('imgur is not responding', 'IMGUR IS DOWN!')
			return
		imgur_json = imgur_response.json()
		if 'mp4' in imgur_json['data']:
			vid_url = imgur_json['data']['mp4']
			vid_name = id
		if 'link' in imgur_json['data']:
			gif_url = imgur_json['data']['link']

	elif 'i.redd.it' in url:
		if '.gif' not in url:
			inbox_item.handle_exception('file is not a gif', 'THERE\'S NO GIF IN HERE!')
			return
		gif_url = url

	elif 'v.redd.it' in url:
		vid_name = submission.id
		media = None
		if hasattr(submission, 'secure_media'):
			media = submission.secure_media
		cross = None
		if hasattr(submission, 'crosspost_parent_list'):
			cross = submission.crosspost_parent_list
		if media is not None and 'reddit_video' in media and 'fallback_url' in media['reddit_video']:
			vid_url = media['reddit_video']['fallback_url']
		elif cross is not None and len(cross) > 0 and 'secure_media' in cross[0] and 'reddit_video' in cross[0]['secure_media'] and 'fallback_url' in cross[0]['secure_media']['reddit_video']:
			vid_url = cross[0]['secure_media']['reddit_video']['fallback_url']
		else:
			inbox_item.handle_exception('can\'t find good url', '')
			return

	elif 'gfycat' in url:
		regex = re.compile(r'http(s*)://(.*)gfycat.com/([0-9A-Za-z]+)', re.I)
		gfy_name = regex.findall(url)[0][2]
		vid_name = gfy_name
		client = GfycatClient(GFYCAT_CLIENT_ID, GFYCAT_CLIENT_SECRET)
		query = client.query_gfy(gfy_name)
		if 'mp4Url' in query['gfyItem']:
			vid_url = query['gfyItem']['mp4Url']
		if 'gifUrl' in query['gfyItem']:
			gif_url = query['gfyItem']['gifUrl']

	uploaded_url = None
	if vid_url is not None:
		if await downloadfile(vid_name, vid_url, inbox_item):
			uploaded_url = await extractFrameFromVid(vid_name, inbox_item)

	elif gif_url is not None:
		gif_response = requests.get(gif_url)
		gif = BytesIO(gif_response.content)
		uploaded_url = await extractFrameFromGif(gif, inbox_item)

	if uploaded_url is not None:
		inbox_item.reply_to_item('Here is the last frame: {}'.format(uploaded_url))
	else:
		print('Error: They shouldn\'t have gotten here.')
#		inbox_item.handle_exception('uploaded_url is None', 'THERE\'S NO GIF IN HERE!')

if __name__ == "__main__":
	while True:
		try:
			inbox_item = None
			r = _init_reddit()
			SUBREDDIT = 'gifendore_testing' if _is_testing_environ else 'gifendore'
			print('polling for new mentions...')
			inbox_stream = r.inbox.stream(pause_after=-1)
			subreddit_stream = r.subreddit(SUBREDDIT).stream.submissions(pause_after=-1, skip_existing=True)
			while True:
				for item in inbox_stream:
					if item is None:
						break
#					always mark the item as read
					if MARK_READ:
						item.mark_read()
					if _is_testing_environ and item.author not in r.subreddit(SUBREDDIT).moderator():
						continue
#					do nothing if it isn't a comment or if it was a reply
					if item.was_comment and isinstance(item, Comment) and 'reply' not in item.subject:
						inbox_item = InboxItem(item, item.submission)
						print('{} by {} in {}'.format(item.subject, item.author.name, item.subreddit_name_prefixed))
						asyncio.run(process_inbox_item(inbox_item))
				for item in subreddit_stream:
					if item is None:
						break
					if _is_testing_environ and item.author not in r.subreddit(SUBREDDIT).moderator():
						continue
					if isinstance(item, Submission):
						inbox_item = InboxItem(item, item)
						print('submission by {} in {}'.format(item.author.name, item.subreddit))
						asyncio.run(process_inbox_item(inbox_item))

		except KeyboardInterrupt:
			print('\nExiting...')
			break

		except prawcore.exceptions.ResponseException as e:
			print('ResponseError: {}'.format(e))
			time.sleep(SLEEP_TIME)

		except prawcore.exceptions.RequestException as e:
			print('RequestError: {}'.format(e))
			time.sleep(SLEEP_TIME)

		except Exception as e:
			try:
				if inbox_item is not None:
					inbox_item.handle_exception(e, '')
				else:
					print('Error: {}'.format(e))
					if not _is_testing_environ:
						logger.exception(e)
			except:
				pass

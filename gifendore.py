import praw, prawcore, requests, sys, re, asyncio, airbrake, time
from os import remove, environ
from decorators import async_timer
from praw.models import Comment
from gfycat.client import GfycatClient
from base64 import b64encode
from PIL import Image
from cv2 import VideoCapture, CAP_PROP_POS_FRAMES, CAP_PROP_FRAME_COUNT
from io import BytesIO
from bs4 import BeautifulSoup

IMGUR_CLIENT_ID = environ['IMGUR_CLIENT_ID']
IMGUR_CLIENT_SECRET = environ['IMGUR_CLIENT_SECRET']
GFYCAT_CLIENT_ID = environ['GFYCAT_CLIENT_ID']
GFYCAT_CLIENT_SECRET = environ['GFYCAT_CLIENT_SECRET']
SUCCESS_TEMPLATE_ID = environ['SUCCESS_TEMPLATE_ID']
ERROR_TEMPLATE_ID = environ['ERROR_TEMPLATE_ID']
AIRBRAKE_API_KEY = environ['AIRBRAKE_API_KEY']
AIRBRAKE_PROJECT_ID = environ['AIRBRAKE_PROJECT_ID']
REDDIT_CLIENT_ID = environ['REDDIT_CLIENT_ID']
REDDIT_CLIENT_SECRET = environ['REDDIT_CLIENT_SECRET']
REDDIT_CLIENT_ID_TESTING = environ['REDDIT_CLIENT_ID_TESTING']
REDDIT_CLIENT_SECRET_TESTING = environ['REDDIT_CLIENT_SECRET_TESTING']
REDDIT_USERNAME = environ['REDDIT_USERNAME']
REDDIT_USERNAME_TESTING = environ['REDDIT_USERNAME_TESTING']
REDDIT_PASSWORD = environ['REDDIT_PASSWORD']

#BOT_FOOTER = '\n\n^(**beep boop beep** I\'m a bot! Come join me [here](https://www.reddit.com/r/gifendore).)'
BOT_FOOTER = '\n\n^(**beep boop beep**) I\'m a bot! | [Subreddit](https://www.reddit.com/r/gifendore) | [Issues](https://s.reddit.com/channel/1698661_674bd7a57e2751c0cc0cca80e84fade432f276e3).'
SLEEP_TIME = 5
MARK_READ = True

logger = airbrake.getLogger(api_key=AIRBRAKE_API_KEY, project_id=AIRBRAKE_PROJECT_ID)

_is_testing_environ = False

def _init_reddit():
	'''initialize the reddit instance'''
	global _is_testing_environ
	if len(sys.argv) > 1 and sys.argv[1] == 'production':
		return praw.Reddit(client_id=REDDIT_CLIENT_ID,
			client_secret=REDDIT_CLIENT_SECRET,
			password=REDDIT_PASSWORD,
			user_agent='mobile:gifendore:0.1 (by /u/brandawg93)',
			username=REDDIT_USERNAME) # Note: Be sure to change the user-agent to something unique.
	else:
		print('using testing environment')
		_is_testing_environ = True
		return praw.Reddit(client_id=REDDIT_CLIENT_ID_TESTING,
			client_secret=REDDIT_CLIENT_SECRET_TESTING,
			password=REDDIT_PASSWORD,
			user_agent='mobile:gifendore:0.1 (by /u/brandawg93)',
			username=REDDIT_USERNAME_TESTING) # Note: Be sure to change the user-agent to something unique.

async def extractFrameFromGif(inGif, comment, submission):
	'''extract frame from gif'''
	frame_num = check_for_args(comment)
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

	return uploadToImgur(buffer, comment, submission)

async def extractFrameFromVid(name, comment, submission):
	'''extract frame from vid'''
	frame_num = check_for_args(comment)
	print('extracting frame {} from video'.format(frame_num))
	name += ".mp4"
	buffer = BytesIO()
	try:
		cap = VideoCapture(name)
		if frame_num > cap.get(CAP_PROP_FRAME_COUNT):
			frame_num = cap.get(CAP_PROP_FRAME_COUNT)

		cap.set(CAP_PROP_POS_FRAMES, cap.get(CAP_PROP_FRAME_COUNT) - frame_num)
		ret, img = cap.read()
		cap.release()

		image = Image.fromarray(img)

		b, g, r = image.split()
		image = Image.merge("RGB", (r, g, b))
		image.save(buffer, format='PNG')
		remove(name)
		return uploadToImgur(buffer, comment, submission)

	except Exception as e:
		try:
			remove(name)
		except OSError:
			pass
		raise e

def uploadToImgur(bytes, comment, submission):
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
		_handle_exception('imgur is not responding', comment, submission, 'IMGUR IS DOWN!')
		return None

	uploaded_url = None
	json = response.json()
	if 'link' in json['data']:
		uploaded_url = json['data']['link']
	print('image uploaded to {}'.format(uploaded_url))
	return uploaded_url

@async_timer
async def downloadfile(name, url):
	print('downloading {}'.format(url))
	url_content = requests.get(url)
	if url_content.status_code == 500:
		_handle_exception('download is not responding', comment, submission, 'HOSTED SITE IS DOWN!')
		return False

	with open('{}.mp4'.format(name),'wb') as file:
		[file.write(chunk) for chunk in url_content.iter_content(chunk_size=255) if chunk]
	return True

def check_for_args(item):
	try:
		html = item.body_html
		soup = BeautifulSoup(html, 'html.parser')
		soup.find('p')
		mention = 'u/gifendore_testing' if _is_testing_environ else 'u/gifendore'
		words = soup.text.strip().split(' ')
		num = int(words[words.index(mention) + 1])
		if isinstance(num, int):
			return num
		else:
			return 1
	except:
		return 1

def _handle_exception(exception, comment, submission, reply_msg):
	print('Error: {}'.format(exception))
	comment.reply('(╯°□°）╯︵ ┻━┻ {}{}'.format(reply_msg, BOT_FOOTER))
	if comment.subreddit_name_prefixed == 'r/gifendore':
		submission.flair.select(ERROR_TEMPLATE_ID)
	if not _is_testing_environ:
		logger.exception(exception)

async def process_inbox_item(item, submission):
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
			_handle_exception('imgur is not responding', item, submission, 'IMGUR IS DOWN!')
			return
		imgur_json = imgur_response.json()
		if 'mp4' in imgur_json['data']:
			vid_url = imgur_json['data']['mp4']
			vid_name = id
		if 'link' in imgur_json['data']:
			gif_url = imgur_json['data']['link']

	elif 'i.redd.it' in url:
		if '.gif' not in url:
			_handle_exception('file is not a gif', item, submission, 'THERE\'S NO GIF IN HERE!')
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
			_handle_exception('can\'t find good url', item, submission, '')
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
		if await downloadfile(vid_name, vid_url):
			uploaded_url = await extractFrameFromVid(vid_name, item, submission)

	elif gif_url is not None:
		gif_response = requests.get(gif_url)
		gif = BytesIO(gif_response.content)
		uploaded_url = await extractFrameFromGif(gif, item, submission)

	if uploaded_url is not None:
		item.reply('Here is the last frame: {}{}'.format(uploaded_url, BOT_FOOTER))
		if item.subreddit_name_prefixed == 'r/gifendore':
			submission.flair.select(SUCCESS_TEMPLATE_ID)
		print('reply sent to {}'.format(item.author.name))
	else:
		print('Error: They shouldn\'t have gotten here.')
#		_handle_exception('uploaded_url is None', item, submission, 'THERE\'S NO GIF IN HERE!')

#def submissions_and_comments(r, **kwargs):
#	results = []
#	results.extend(r.subreddit('gifendore').new(**kwargs))
#	results.extend(r.inbox.messages(**kwargs))
#	results.sort(key=lambda post: post.created_utc, reverse=True)
#	return results

if __name__ == "__main__":
	while True:
		try:
			item = None
			submission = None
			r = _init_reddit()
			print('polling for new mentions...')
#			stream = praw.models.util.stream_generator(lambda **kwargs: submissions_and_comments(r, **kwargs))
#			for item in stream:
			for item in r.inbox.stream():
#				always mark the item as read
				if MARK_READ:
					item.mark_read()
				if _is_testing_environ and item.author not in r.subreddit('gifendore').moderator():
					continue
#				do nothing if it isn't a comment or if it was a reply
				if item.was_comment and isinstance(item, Comment) and 'reply' not in item.subject:
					submission = item.submission
					print('{} by {} in {}'.format(item.subject, item.author.name, item.subreddit_name_prefixed))
					print('getting submission with id: {}, url: {}'.format(submission.id, submission.url))
					asyncio.run(process_inbox_item(item, submission))

		except KeyboardInterrupt:
			print('\nExiting...')
			break

		except prawcore.exceptions.ResponseException:
			print('Error: Could not get response from reddit.')
			time.sleep(SLEEP_TIME)

		except prawcore.exceptions.RequestException:
			print('Error: Could not connect to reddit')
			time.sleep(SLEEP_TIME)

		except Exception as e:
			try:
				if item is not None and submission is not None:
					_handle_exception(e, item, submission, '')
				else:
					print('Error: {}'.format(e))
					if not _is_testing_environ:
						logger.exception(e)
			except:
				pass

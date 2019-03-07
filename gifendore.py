import praw
import requests
import os
import sys
import re
import asyncio
import cv2
import airbrake
from gfycat.client import GfycatClient
from base64 import b64encode
from PIL import Image
from io import BytesIO

IMGUR_CLIENT_ID = os.environ['IMGUR_CLIENT_ID']
IMGUR_CLIENT_SECRET = os.environ['IMGUR_CLIENT_SECRET']
GFYCAT_CLIENT_ID = os.environ['GFYCAT_CLIENT_ID']
GFYCAT_CLIENT_SECRET = os.environ['GFYCAT_CLIENT_SECRET']
SUCCESS_TEMPLATE_ID = os.environ['SUCCESS_TEMPLATE_ID']
ERROR_TEMPLATE_ID = os.environ['ERROR_TEMPLATE_ID']
AIRBRAKE_API_KEY = os.environ['AIRBRAKE_API_KEY']
AIRBRAKE_PROJECT_ID = os.environ['AIRBRAKE_PROJECT_ID']
REDDIT_CLIENT_ID = os.environ['REDDIT_CLIENT_ID']
REDDIT_CLIENT_SECRET = os.environ['REDDIT_CLIENT_SECRET']
REDDIT_CLIENT_ID_TESTING = os.environ['REDDIT_CLIENT_ID_TESTING']
REDDIT_CLIENT_SECRET_TESTING = os.environ['REDDIT_CLIENT_SECRET_TESTING']
REDDIT_USERNAME = os.environ['REDDIT_USERNAME']
REDDIT_USERNAME_TESTING = os.environ['REDDIT_USERNAME_TESTING']
REDDIT_PASSWORD = os.environ['REDDIT_PASSWORD']

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

def extractFrameFromGif(inGif, comment, submission):
	'''extract frame from gif'''
	print('extracting frame from gif')
	try:
		frame = Image.open(inGif)
		frame.seek(frame.n_frames - 1)
		buffer = BytesIO()
		frame.save(buffer, format='PNG')
#		check if its transparent
		colors = frame.convert('RGBA').getcolors()
		if len(colors) == 1 and colors[0][-1][-1] == 0:
			_handle_exception('frame is transparent', comment, 'THIS GIF IS TOO BIG!')
			return None

		return uploadToImgur(buffer, submission)
	except Exception as e:
		_handle_exception(e, comment, submission, 'CAN\'T GET FRAME FROM GIF!')
		return None

def extractFrameFromVid(name, comment, submission):
	'''extract frame from vid'''
	print('extracting frame from video')
	name += ".mp4"
	buffer = BytesIO()
	try:
		cap = cv2.VideoCapture(name)
		cap.set(cv2.CAP_PROP_POS_FRAMES, cap.get(cv2.CAP_PROP_FRAME_COUNT) - 1)
		ret, img = cap.read()
		cap.release()

		image = Image.fromarray(img)

		b, g, r = image.split()
		image = Image.merge("RGB", (r, g, b))
		image.save(buffer, format='PNG')
		os.remove(name)
		return uploadToImgur(buffer, submission)

	except Exception as e:
		_handle_exception(e, comment, submission, 'CAN\'T GET FRAME FROM VIDEO!')
		os.remove(name)
		return None

def uploadToImgur(bytes, submission):
	'''upload the frame to imgur'''
	try:
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
		uploaded_url = None
		json = response.json()
		if 'link' in json['data']:
			uploaded_url = json['data']['link']
		print('image uploaded to {}'.format(uploaded_url))
		return uploaded_url
	except Exception as e:
		_handle_exception(e, comment, submission, 'CAN\'T UPLOAD TO IMGUR!')

def downloadfile(name, url):
	print('downloading {}'.format(url))
	url_content = requests.get(url)
	with open('{}.mp4'.format(name),'wb') as file:
		[file.write(chunk) for chunk in url_content.iter_content(chunk_size=255) if chunk]

def _handle_exception(exception, comment, submission, reply_msg):
	print(exception)
	comment.reply('(╯°□°）╯︵ ┻━┻ {}\n\n^(**beep boop beep** I\'m a bot! Come join me [here](https://www.reddit.com/r/gifendore).)'.format(reply_msg))
	submission.flair.select(ERROR_TEMPLATE_ID)
	logger.exception(exception)

async def process_inbox_item(item, comment, submission):
#	testing for v.redd.it
#	submission = r.submission(id='avu67x')
	response = requests.get(submission.url)
	print('extracting gif from {}'.format(submission.url))
	url = response.url
	gif_url = None
	vid_url = None
	vid_name = None
	comment = r.comment(id=item.id)
	if 'i.imgur' in url:

		regex = re.compile(r'https://i\.imgur\.com/(.*?)\.', re.I)
		id = regex.findall(url)[0]

		imgur_response = requests.get('https://api.imgur.com/3/image/{}'.format(id))
		imgur_json = imgur_response.json()
		if 'mp4' in imgur_json['data']:
			vid_url = imgur_json['data']['mp4']
			vid_name = id
		if 'link' in imgur_json['data']:
			gif_url = imgur_json['data']['link']

	elif 'i.redd.it' in url:
		if '.gif' not in url:
			_handle_exception('file is not a gif', comment, submission, 'THERE\'S NO GIF IN HERE!')
			return

		gif_url = url

	elif 'v.redd.it' in submission.url:
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
			_handle_exception('can\'t find good url', comment, submission, '')
			return

	elif 'gfycat' in url:
		regex = re.compile(r'https://gfycat.com/(.+)', re.I)
		gfy_name = regex.findall(url)[0]
		vid_name = gfy_name
		client = GfycatClient(GFYCAT_CLIENT_ID, GFYCAT_CLIENT_SECRET)
		query = client.query_gfy(gfy_name)
		if 'mp4Url' in query['gfyItem']:
			vid_url = query['gfyItem']['mp4Url']
		if 'gifUrl' in query['gfyItem']:
			gif_url = query['gfyItem']['gifUrl']

	uploaded_url = None
	if vid_url is not None:
		downloadfile(vid_name, vid_url)
		uploaded_url = extractFrameFromVid(vid_name, comment, submission)

	elif gif_url is not None:
		gif_response = requests.get(gif_url)
		gif = BytesIO(gif_response.content)
		uploaded_url = extractFrameFromGif(gif, comment, submission)

	if uploaded_url is not None:
		comment.reply('Here is the last frame: {}\n\n^(**beep boop beep** I\'m a bot! Come join me [here](https://www.reddit.com/r/gifendore).)'.format(uploaded_url))
		if item.subreddit_name_prefixed == 'r/gifendore':
			submission.flair.select(SUCCESS_TEMPLATE_ID)
		print('reply sent to {}'.format(item.author.name))
	else:
		_handle_exception('uploaded_url is None', comment, submission, 'THERE\'S NO GIF IN HERE!')

if __name__ == "__main__":
	while(True):
		try:
			r = _init_reddit()
			print('polling for new mentions...')
			for item in r.inbox.stream():
#				print(vars(item))
#				always mark the item as read
				item.mark_read()
				if _is_testing_environ:
					if item.author not in r.subreddit('gifendore').moderator():
						continue
				comment = None
				submission = None
#				do nothing if it isn't a comment or if it was a reply
				if item.was_comment and 'reply' not in item.subject:
					try:
						comment = r.comment(id=item.id)
						parent_link = comment.link_id[3:]
						submission = r.submission(id=parent_link)
						if parent_link is not None:
							print('{} by {} in {}'.format(item.subject, item.author.name, item.subreddit_name_prefixed))
							print('getting submission with id: {}'.format(parent_link))
							asyncio.run(process_inbox_item(item, comment, submission))
					except Exception as e:
						if comment is not None and submission is not None:
							_handle_exception(e, comment, submission, '')
						else:
							print(e)
							logger.exception(e)
		except Exception as e:
			logger.exception(e)

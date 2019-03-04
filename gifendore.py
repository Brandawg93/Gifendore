import praw
import requests
import os
import re
import asyncio
import cv2
from gfycat.client import GfycatClient
from base64 import b64encode
from PIL import Image
from io import BytesIO

IMGUR_CLIENT_ID = '***REMOVED***'
IMGUR_CLIENT_SECRET = '***REMOVED***'
GFYCAT_CLIENT_ID = '2_zqrJyE'
GFYCAT_CLIENT_SECRET = '***REMOVED***'
SUCCESS_TEMPLATE_ID = 'faf4254a-3ec7-11e9-b8c3-0ef638bf5928'
ERROR_TEMPLATE_ID = '88036b28-3ecb-11e9-8f2e-0e08d49461be'

def _init_reddit():
	'''initialize the reddit instance'''
	return praw.Reddit(client_id='***REMOVED***',
		client_secret='***REMOVED***',
		password='***REMOVED***',
		user_agent='mobile:gifendore:0.1 (by /u/brandawg93)',
		username='gifendore') # Note: Be sure to change the user-agent to something unique.

def extractFrameFromGif(inGif, comment, submission):
	'''extract frame from gif'''
	print('extracting frame from gif')
	try:
		frame = Image.open(inGif)
		frame.seek(frame.n_frames - 1)
		buffer = BytesIO()
		frame.save(buffer, format='PNG')
		#check if its transparent
		colors = frame.convert('RGBA').getcolors()
		if len(colors) == 1 and colors[0][-1][-1] == 0:
			_handle_exception('frame is transparent', comment, 'THIS GIF IS TOO BIG!')
			return None

		return uploadToImgur(buffer)
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
		uploaded_url = response.json()['data']['link']
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
	comment.reply('(╯°□°）╯︵ ┻━┻ {}'.format(reply_msg))
	submission.flair.select(ERROR_TEMPLATE_ID)

async def process_inbox_item(item, comment, submission):
#	print(vars(item))
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
		if submission.secure_media is not None:
			vid_url = submission.secure_media['reddit_video']['fallback_url']
		elif submission.crosspost_parent_list is not None:
			vid_url = submission.crosspost_parent_list[0]['secure_media']['reddit_video']['fallback_url']
		else:
			_handle_exception('can\'t find good url', comment, submission, '')
			return

	elif 'gfycat' in url:
		regex = re.compile(r'https://gfycat.com/(.+)', re.I)
		gfy_name = regex.findall(url)[0]
		vid_name = gfy_name
		client = GfycatClient(GFYCAT_CLIENT_ID, GFYCAT_CLIENT_SECRET)
		query = client.query_gfy(gfy_name)
		vid_url = query['gfyItem']['mp4Url']
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
		comment.reply('Here is the last frame: {}'.format(uploaded_url))
		if item.subreddit_name_prefixed == 'r/gifendore':
			submission.flair.select(SUCCESS_TEMPLATE_ID)
		print('reply sent to {}'.format(item.author.name))
	else:
		_handle_exception('uploaded_url is None', comment, submission, 'THIS GIF IS NO GOOD!')
		return

if __name__ == "__main__":
	r = _init_reddit()
	print('polling for new mentions...')
	for item in r.inbox.stream():
#		always mark the item as read
		item.mark_read()
		comment = None
		submission = None
#		do nothing if it isn't a comment
		if item.was_comment:
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

import praw
import requests
import os
import re
import asyncio
from base64 import b64encode
from PIL import Image
from io import BytesIO

IMGUR_CLIENT_ID = '***REMOVED***'
IMGUR_CLIENT_SECRET = '***REMOVED***'
GFYCAT_CLIENT_ID = '2_zqrJyE'
GFYCAT_CLIENT_SECRET = '***REMOVED***'

def _init_reddit():
	'''initialize the reddit instance'''
	return praw.Reddit(client_id='***REMOVED***',
		client_secret='***REMOVED***',
		password='***REMOVED***',
		user_agent='mobile:gifendore:0.1 (by /u/brandawg93)',
		username='gifendore') # Note: Be sure to change the user-agent to something unique.

def extractFrameFromGif(inGif, comment):
	'''extract frame from gif'''
	try:
		frame = Image.open(inGif)
		print('extracting frame')
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
		return None

def extractFrameFromVid(name, comment):
	'''extract frame from vid'''
	name += ".mp4"
	buffer = BytesIO()
	print('extracting frame')
	try:
		import cv2
		cap = cv2.VideoCapture(name)
		cap.set(cv2.CAP_PROP_POS_FRAMES, cap.get(cv2.CAP_PROP_FRAME_COUNT)-1)
		ret, img = cap.read()
		cap.release()

		image = Image.fromarray(img)

		b, g, r = image.split()
		image = Image.merge("RGB", (r, g, b))
		image.save(buffer, format='PNG')

	except ImportError:
		try:
			from contextlib import closing
			from videosequence import VideoSequence

			with closing(VideoSequence(name)) as frames:
				buffer = BytesIO()
				frames[-1].save(buffer, format='PNG')
		except Exception as e:
			print(e)
			os.remove(name)
			return None
	except Exception as e:
		print(e)
		os.remove(name)
		return None

	os.remove(name)
	return uploadToImgur(buffer)

def uploadToImgur(bytes):
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
		_handle_exception(e, comment, '')

def downloadfile(name, url):
	print('downloading {}'.format(url))
	name += ".mp4"
	r=requests.get(url)
	f=open(name,'wb');
	for chunk in r.iter_content(chunk_size=255):
		if chunk: # filter out keep-alive new chunks
			f.write(chunk)
	f.close()

def _handle_exception(exception, comment, reply_msg):
	print(exception)
	comment.reply('(╯°□°）╯︵ ┻━┻ {}'.format(reply_msg))

async def process_inbox_item(item):
#	print(vars(item))
	if item.subject == 'username mention':
		print('{} by {} in {}'.format(item.subject, item.author.name, item.subreddit_name_prefixed))
		item.mark_read()
		print('getting submission with id: {}'.format(item.parent_id[3:]))
		submission = r.submission(id=item.parent_id[3:])
#		testing for v.redd.it
#		submission = r.submission(id='avu67x')
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
			imgur_link = imgur_response.json()['data']['link']
			if '.mp4' in imgur_link:
				vid_url = imgur_link
				vid_name = id
			elif '.gif' in imgur_link:
				gif_url = imgur_link

		elif 'i.redd.it' in url:
			if '.gif' not in url:
				_handle_exception('file is not a gif', comment, 'THERE\'S NO GIF IN HERE!')
				return

			gif_url = url
		elif 'v.redd.it' in submission.url:
			vid_name = submission.id
			if submission.secure_media is not None:
				vid_url = submission.secure_media['reddit_video']['fallback_url']
			elif submission.crosspost_parent_list is not None:
				vid_url = submission.crosspost_parent_list[0]['secure_media']['reddit_video']['fallback_url']
			else:
					_handle_exception('can\'t find good url', comment, '')

		elif 'gfycat' in url:
			from gfycat.client import GfycatClient
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
			uploaded_url = extractFrameFromVid(vid_name, comment)

		elif gif_url is not None:
			gif_response = requests.get(gif_url)
			gif = BytesIO(gif_response.content)
			uploaded_url = extractFrameFromGif(gif, comment)

		if uploaded_url is not None:
			comment.reply('Here is the last frame: {}'.format(uploaded_url))
			print('reply sent to {}'.format(item.author.name))
		else:
			_handle_exception('uploaded_url is None', comment, 'THIS GIF IS NO GOOD!')

if __name__ == "__main__":
	r = _init_reddit()
	print('polling for new mentions...')
	for item in r.inbox.stream():
		try:
			asyncio.run(process_inbox_item(item))
		except Exception as e:
			print(e)

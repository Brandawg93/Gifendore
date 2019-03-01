import praw
import requests
import os
import re
from base64 import b64encode
from PIL import Image
from io import BytesIO

IMGUR_CLIENT_ID = '***REMOVED***'
IMGUR_CLIENT_SECRET = '***REMOVED***'

def _init_reddit():
	'''initialize the reddit instance'''
	return praw.Reddit(client_id='***REMOVED***',
		client_secret='***REMOVED***',
		password='***REMOVED***',
		user_agent='mobile:gifendore:0.1 (by /u/brandawg93)',
		username='gifendore') # Note: Be sure to change the user-agent to something unique.

def extractFrames(inGif, comment):
	'''extract frame from gif'''
	try:
		frame = Image.open(inGif)
		print('extracting frame')
		frame.seek(frame.n_frames - 1)
		buffer = BytesIO()
		frame.save(buffer, format='PNG')
		return uploadToImgur(buffer)
	except Exception as e:
		_handle_exception(e, comment, '')

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

def _handle_exception(exception, comment, reply_msg):
	print(exception)
	comment.reply('(╯°□°）╯︵ ┻━┻ {}'.format(reply_msg))

if __name__ == "__main__":
	r = _init_reddit()
	print('polling for new mentions...')
	for item in r.inbox.stream():
#		print(vars(item))
		if item.subject == 'username mention':
			print('{} by {} in {}'.format(item.subject, item.author.name, item.subreddit_name_prefixed))
			item.mark_read()
			print('getting submission with id: {}'.format(item.parent_id[3:]))
			submission = r.submission(id=item.parent_id[3:])
			response = requests.get(submission.url)
			url = response.url
			print('extracting gif from {}'.format(response.url))
			gif_url = None
			if 'i.imgur' in url:
				if '.gif' not in url:
					_handle_exception(comment, 'THERE\'S NO GIF IN HERE!')
					continue
				regex = re.compile(r'https://i.imgur.com/(.*?)\.gif', re.I)
				id = regex.findall(url)[0]
				gif_url = 'https://imgur.com/download/{}'.format(id)
			elif 'i.redd.it' in url:
				gif_url = url

			comment = r.comment(id=item.id)
			if gif_url is not None and '.gif' in gif_url:
				gif_response = requests.get(gif_url)
				gif = BytesIO(gif_response.content)
				uploaded_url = extractFrames(gif, comment)
				comment.reply('Here is the last frame of the gif: {}'.format(uploaded_url))
			elif gif_url is None:
				_handle_exception('gif_url is None', comment, 'THIS GIF IS NO GOOD!')
			else:
				_handle_exception('file is not a gif', comment, 'THERE\'S NO GIF IN HERE!')

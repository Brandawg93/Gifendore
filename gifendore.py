import praw
import requests
import os
import re
from contextlib import closing
from videosequence import VideoSequence
from base64 import b64encode
from PIL import Image
from io import BytesIO
from gfycat.client import GfycatClient

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
		_handle_exception(e, comment, '')
		return None

def extractFrameFromVid(name, comment):
	'''extract frame from vid'''
	name += ".mp4"
	try:
		with closing(VideoSequence(name)) as frames:
			buffer = BytesIO()
			frames[-1].save(buffer, format='PNG')
		os.remove(name)
		return uploadToImgur(buffer)
	except Exception as e:
		_handle_exception(e, comment, '')
		return None

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
	name += ".mp4"
	r=requests.get(url)
	f=open(name,'wb');
	print("Donloading.....")
	for chunk in r.iter_content(chunk_size=255): 
		if chunk: # filter out keep-alive new chunks
			f.write(chunk)
	print("Done")
	f.close()

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
#			item.mark_read()
			print('getting submission with id: {}'.format(item.parent_id[3:]))
			submission = r.submission(id=item.parent_id[3:])
			response = requests.get(submission.url)
			url = response.url
			print('extracting gif from {}'.format(response.url))
			gif_url = None
			vid_url = None
			vid_name = None
			comment = r.comment(id=item.id)
			if 'i.imgur' in url:
				if '.gif' not in url:
					_handle_exception('file is not a gif', comment, 'THERE\'S NO GIF IN HERE!')
					continue

				regex = re.compile(r'https://i.imgur.com/(.*?)\.gif', re.I)
				id = regex.findall(url)[0]
				gif_url = 'https://imgur.com/download/{}'.format(id)
			elif 'i.redd.it' in url:
				if '.gif' not in url:
					_handle_exception('file is not a gif', comment, 'THERE\'S NO GIF IN HERE!')
					continue

				gif_url = url
			elif 'v.redd.it' in url:
				print(submission)
				continue
				
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
				print(vid_url)
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
import re

class BaseHost:
	def __init__(self, url_text, regex=r''):
		self.url_text = url_text
		self.regex = re.compile(regex, re.I)
		self.vid_url = None
		self.gif_url = None
		self.img_url = None
		self.name = None

	def is_host(self, url):
		return self.url_text in url

	def get_info(self):
		return self.vid_url, self.gif_url, self.img_url, self.name

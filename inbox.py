import sys
from os import environ
from praw.models import Submission
from bs4 import BeautifulSoup

SUCCESS_TEMPLATE_ID = environ['SUCCESS_TEMPLATE_ID']
ERROR_TEMPLATE_ID = environ['ERROR_TEMPLATE_ID']
BOT_FOOTER = '\n\n^(**beep boop beep**) I\'m a bot! | [Subreddit](https://www.reddit.com/r/gifendore) | [Issues](https://s.reddit.com/channel/1698661_674bd7a57e2751c0cc0cca80e84fade432f276e3).'

class InboxItem:
	def __init__(self, item, submission):
		self.item = item
		self.submission = submission
		print('getting submission with id: {}'.format(submission.id))

	def handle_exception(self, exception, reply_msg):
		print('Error: {}'.format(exception))
		self.reply_to_item('(╯°□°）╯︵ ┻━┻ {}'.format(reply_msg, is_error=True))
		if not _is_testing_environ:
			logger.exception(exception)

	def reply_to_item(self, message, is_error=False):
		reply = self.item.reply('{}{}'.format(message, BOT_FOOTER))
		if self.item.subreddit in ['gifendore', 'gifendore_testing']:
			if self.item.subreddit == 'gifendore':
				if is_error:
					self.submission.flair.select(ERROR_TEMPLATE_ID)
				else:
					self.submission.flair.select(SUCCESS_TEMPLATE_ID)
			if isinstance(self.item, Submission):
				reply.mod.distinguish(sticky=True)
		if not is_error:
			print('reply sent to {}'.format(self.item.author.name))

	def check_for_args(self):
		_is_testing_environ = not (len(sys.argv) > 1 and sys.argv[1] == 'production')
		try:
			if isinstance(self.item, Submission):
				return 0
			html = self.item.body_html
			soup = BeautifulSoup(html, 'html.parser')
			soup.find('p')
			mention = 'u/gifendore_testing' if _is_testing_environ else 'u/gifendore'
			words = soup.text.strip().split(' ')
			num = int(words[words.index(mention) + 1])
			if isinstance(num, int):
				return num
			else:
				return 0
		except:
			return 0

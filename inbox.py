import sys, requests, asyncio, exceptions
from os import environ
from praw.models import Comment, Submission
from bs4 import BeautifulSoup
from exceptions import InvalidItemError

SUCCESS_TEMPLATE_ID = environ['SUCCESS_TEMPLATE_ID']
ERROR_TEMPLATE_ID = environ['ERROR_TEMPLATE_ID']
BOT_FOOTER = '\n\n^(**beep boop beep**) I\'m a bot! | [Subreddit](https://www.reddit.com/r/gifendore) | [Issues](https://s.reddit.com/channel/1698661_674bd7a57e2751c0cc0cca80e84fade432f276e3).'

class InboxItem:
	def __init__(self, item):
		self._is_testing_environ = not (len(sys.argv) > 1 and sys.argv[1] == 'production')
		self.item = item
		if isinstance(item, Comment):
			self.submission = item.submission
		elif isinstance(item, Submission):
			self.submission = item
		else:
			raise InvalidItemError('Item is invalid')

		print('getting submission with id: {}'.format(self.submission.id))
		if isinstance(item, Comment):
			print('{} by {} in {}'.format(item.subject, item.author.name, item.subreddit_name_prefixed))
		elif isinstance(item, Submission):
			print('submission by {} in {}'.format(item.author.name, item.subreddit))
		else:
			raise TypeError('item is not Comment or Submission')

	async def handle_exception(self, exception, reply_msg=''):
		table_flip = '(╯°□°）╯︵ ┻━┻'
		print('Error: {}'.format(exception))
		try:
			if isinstance(exception, requests.exceptions.ConnectionError):
				await self.reply_to_item('{} {}'.format(table_flip, "CANT'T CONNECT TO HOST!", is_error=True))
			elif isinstance(exception, requests.exceptions.Timeout):
				await self.reply_to_item('{} {}'.format(table_flip, "HOST TIMED OUT!", is_error=True))
			elif isinstance(exception, requests.exceptions.HTTPError):
				await self.reply_to_item('{} {}'.format(table_flip, "HOST IS DOWN!", is_error=True))
			elif isinstance(exception, exceptions.InvalidHostError):
				await self.reply_to_item('{} {}'.format(table_flip, "CAN'T GET GIFS FROM THIS SITE!", is_error=True))
			else:
				await self.reply_to_item('{} {}'.format(table_flip, reply_msg, is_error=True))

			if not _is_testing_environ:
				logger.exception(exception)
		except:
			pass

	async def reply_to_item(self, message, is_error=False, upvote=False):
		reply = self.item.reply('{}{}'.format(message, BOT_FOOTER))
		if upvote:
			self.item.upvote()
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

	async def crosspost_and_pm_user(self):
		sub = 'gifendore_testing' if self._is_testing_environ else 'gifendore'
		crosspost = self.submission.crosspost(sub, send_replies=False)
		reply = self.item.author.message('gifendore here!', 'Unfortunately, I am banned from r/{}. But have no fear! I have crossposted this to r/{}! You can view it [here]({}).{}'.format(self.submission.subreddit.display_name, sub, crosspost.shortlink, BOT_FOOTER))

	def check_for_args(self):
		_is_testing_environ = not (len(sys.argv) > 1 and sys.argv[1] == 'production')
		try:
			if isinstance(self.item, Submission):
				return 0.0
			html = self.item.body_html
			soup = BeautifulSoup(html, 'html.parser')
			soup.find('p')
			mention = 'u/gifendore_testing' if _is_testing_environ else 'u/gifendore'
			words = soup.text.strip().split(' ')
			num = float(words[words.index(mention) + 1])
			if isinstance(num, float):
				return abs(num)
			else:
				return 0.0
		except:
			return 0.0

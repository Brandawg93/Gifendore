import sys, requests, asyncio, logging
from core.exceptions import InvalidHostError
from praw.exceptions import APIException
from prawcore.exceptions import Forbidden
from core.memory import UserMemory
from core.config import config
from services import ab_logger
from os import environ
from praw.models import Comment, Submission
from bs4 import BeautifulSoup

SUCCESS_TEMPLATE_ID = environ['SUCCESS_TEMPLATE_ID']
ERROR_TEMPLATE_ID = environ['ERROR_TEMPLATE_ID']
ISSUE_LINK = '/message/compose?to=/u/brandawg93&subject=Gifendore%20Issue&message=Please%20submit%20any%20issues%20you%20may%20have%20with%20u/gifendore%20here%20along%20with%20a%20link%20to%20the%20original%20post.'
SUBREDDIT_LINK = '/r/gifendore'
GITHUB_LINK = 'https://github.com/Brandawg93/Gifendore'
DONATION_LINK = 'https://paypal.me/brandawg93'
BOT_FOOTER = '\n\n***\n\n^(I am a bot) ^| ^[Subreddit]({}) ^| ^[Issues]({}) ^| ^[Github]({}) ^| ^[Donate]({}) ^❤️'.format(SUBREDDIT_LINK, ISSUE_LINK, GITHUB_LINK, DONATION_LINK)

logger = logging.getLogger("gifendore")

class InboxItem:
	def __init__(self, item):
		self.item = item
		self.marked_as_spam = item.subreddit in config.banned_subs

		if isinstance(item, Comment):
			self.submission = item.submission
			logger.info('{} by {} in {}'.format(item.subject, item.author.name, item.subreddit_name_prefixed))
		elif isinstance(item, Submission):
			self.submission = item
			logger.info('submission by {} in {}'.format(item.author.name, item.subreddit))
		else:
			raise TypeError('item is not Comment or Submission')
		logger.info('getting submission with id: {}'.format(self.submission.id))

	async def handle_exception(self, exception, reply_msg=''):
		'''Log and send exceptions and reply to user'''
		table_flip = '(╯°□°）╯︵ ┻━┻'
		logger.exception(exception)
		try:
			if isinstance(exception, requests.exceptions.ConnectionError):
				await self.reply_to_item('{} {}'.format(table_flip, "CANT'T CONNECT TO HOST!", is_error=True))
			elif isinstance(exception, requests.exceptions.Timeout):
				await self.reply_to_item('{} {}'.format(table_flip, "HOST TIMED OUT!", is_error=True))
			elif isinstance(exception, requests.exceptions.HTTPError):
				if exception.response.status_code == 404:
					await self.reply_to_item('{} {}'.format(table_flip, "GIF WAS DELETED!", is_error=True))
				else:
					await self.reply_to_item('{} {}'.format(table_flip, "HOST IS DOWN!", is_error=True))
			elif isinstance(exception, InvalidHostError):
				await self.reply_to_item('{} {}'.format(table_flip, "CAN'T GET GIFS FROM THIS SITE!", is_error=True))
			else:
				await self.reply_to_item('{} {}'.format(table_flip, reply_msg, is_error=True))

			if not config._is_testing_environ:
				ab_logger.exception(exception)
		except:
			pass

	async def reply_to_item(self, message, is_error=False, upvote=True):
		'''Send link to the user via reply'''
		response = '{}{}'.format(message, BOT_FOOTER if not self.marked_as_spam else '')
		if isinstance(self.item, Submission):
			reply = self.item.reply(response)
		else:
			og_comment = None
			if config._use_memory:
				memory = UserMemory()
				og_comment = memory.get(self.item.author.name, self.item.submission.id)
			if og_comment:
				try:
					reply = config.r.comment(og_comment).edit('EDIT:\n\n{}{}'.format(message, BOT_FOOTER if not self.marked_as_spam else ''))
					subject = 'Comment Edited'
					body = 'I have edited my original comment. You can find it [here]({}).'.format(reply.permalink)
					self.item.author.message(subject, body)
					logger.info('Comment was edited')
				except Forbidden as e:
					logger.info('Comment missing. Sending a new one')
					reply = self.item.reply(response)
					if config._use_memory:
						memory = UserMemory()
						memory.add(self.item.author.name, self.item.submission.id, reply.id)
			else:
				reply = self.item.reply(response)
				if config._use_memory:
					memory = UserMemory()
					memory.add(self.item.author.name, self.item.submission.id, reply.id)
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
		logger.info('reply sent to {}'.format(self.item.author.name))

	async def crosspost_and_pm_user(self):
		'''crosspost to r/gifendore and message user'''
		crosspost = self.submission.crosspost(config.subreddit, send_replies=False)
		reply = self.item.author.message('gifendore here!', 'Unfortunately, I am banned from r/{}. But have no fear! I have crossposted this to r/{}! You can view it [here]({}).{}'.format(self.submission.subreddit.display_name, config.subreddit, crosspost.shortlink, BOT_FOOTER))
		logger.info('Banned from r/{}...Crossposting for user'.format(self.submission.subreddit.display_name))

	async def send_banned_msg(self):
		'''Notify user that they are banned'''
		subject = 'You have been banned from gifendore'
		body = 'Hi u/{}, Unfortunately you are banned from r/gifendore which also means you are banned from using the bot. If you have any questions, please [contact the mods.](http://www.reddit.com/message/compose?to=/r/gifendore)'.format(self.item.author.name)
		reply = self.item.author.message(subject, body)
		logger.info('Banned PM sent to {}'.format(self.item.author.name))

	def check_for_args(self):
		'''Check if there are arguments after the username mention'''
		try:
			if isinstance(self.item, Submission):
				return 0.0
			html = self.item.body_html
			soup = BeautifulSoup(html, 'html.parser')
			soup.find('p')
			mention = 'u/gifendore_testing' if config._is_testing_environ else 'u/gifendore'
			words = [x[1:] if x.startswith('/') else x for x in soup.text.lower().strip().split(' ')]
			num = float(words[words.index(mention) + 1])
			if isinstance(num, float):
				return abs(num)
			else:
				return 0.0
		except:
			return 0.0

import logging
import re
import requests
from os import environ
from praw.models import Comment, Submission
from prawcore.exceptions import Forbidden
from core.config import config
from core.exceptions import InvalidHostError
from core.memory import UserMemory
from services import ab_logger

SUCCESS_TEMPLATE_ID = environ['SUCCESS_TEMPLATE_ID']
ERROR_TEMPLATE_ID = environ['ERROR_TEMPLATE_ID']
ISSUE_LINK = '/message/compose?to=/u/brandawg93&subject=Gifendore%20Issue&message=Please%20submit%20any%20issues%20you%20may%20have%20with%20u/gifendore%20here%20along%20with%20a%20link%20to%20the%20original%20post.'
SUBREDDIT_LINK = '/r/gifendore'
GITHUB_LINK = 'https://github.com/Brandawg93/Gifendore'
DONATION_LINK = 'https://paypal.me/brandawg93'
BOT_FOOTER = '\n\n***\n\n^(I am a bot) ^| ^[Subreddit]({}) ^| ^[Issues]({}) ^| ^[Github]({})️'.format(SUBREDDIT_LINK, ISSUE_LINK, GITHUB_LINK)

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

	async def handle_exception(self, exception, reply_msg=''):
		"""Log and send exceptions and reply to user"""
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

			if not config.is_testing_environ:
				ab_logger.exception(exception)
		except Exception as e:
			logger.exception(e)
			pass

	async def reply_to_item(self, message, is_error=False, upvote=True):
		"""Send link to the user via reply"""
		response = '{}{}'.format(message, BOT_FOOTER if not self.marked_as_spam else '')
		if isinstance(self.item, Submission) and self.item.subreddit in [x.title for x in config.r.user.moderator_subreddits()]:
			reply = self.item.reply(response)
			reply.mod.distinguish(sticky=True)
			if self.item.subreddit == 'gifendore':
				if is_error:
					self.submission.flair.select(ERROR_TEMPLATE_ID)
				else:
					self.submission.flair.select(SUCCESS_TEMPLATE_ID)
		else:
			og_comment = None
			if config.use_memory and not self.should_send_pointers():
				memory = UserMemory()
				og_comment = memory.get(self.item.author.name, self.item.submission.id)
			if og_comment:
				try:
					reply = config.r.comment(og_comment).edit(
						'EDIT:\n\n{}{}'.format(message, BOT_FOOTER if not self.marked_as_spam else ''))
					subject = 'Comment Edited'
					body = 'I have edited my original comment. You can find it [here]({}).{}'.format(reply.permalink, BOT_FOOTER)
					self.item.author.message(subject, body)
					logger.info('Comment was edited')
				except Forbidden as e:
					logger.info('Comment missing. Sending a new one')
					reply = self.item.reply(response)
					if config.use_memory:
						memory = UserMemory()
						memory.add(self.item.author.name, self.item.submission.id, reply.id)
			else:
				reply = self.item.reply(response)
				if config.use_memory:
					memory = UserMemory()
					memory.add(self.item.author.name, self.item.submission.id, reply.id)
		if upvote:
			self.item.upvote()
		logger.info('reply sent to {}'.format(self.item.author.name))

	async def crosspost_and_pm_user(self):
		"""crosspost to r/gifendore and message user"""
		crosspost = self.submission.crosspost(config.subreddit, send_replies=False)
		subject = 'gifendore here!'
		body = 'Unfortunately, I am banned from r/{}. But have no fear! I have crossposted this to r/{}! You can view it [here]({}).{}'.format(self.submission.subreddit.display_name, config.subreddit, crosspost.shortlink, BOT_FOOTER)
		reply = self.item.author.message(subject, body)
		logger.info('Banned from r/{}...Crossposting for user'.format(self.submission.subreddit.display_name))

	async def send_banned_msg(self):
		"""Notify user that they are banned"""
		subject = 'You have been banned from gifendore'
		body = 'Hi u/{}, Unfortunately you are banned from r/gifendore which also means you are banned from using the bot. If you have any questions, please [contact the mods.](http://www.reddit.com/message/compose?to=/r/gifendore)'.format(
			self.item.author.name)
		reply = self.item.author.message(subject, body)
		logger.info('Banned PM sent to {}'.format(self.item.author.name))

	def should_send_pointers(self):
		"""Check if pointer easter egg should be sent"""
		return True if re.search('.+points (?:to|for).+gifendore.*', self.item.body.lower(), re.IGNORECASE) else False

	def check_for_args(self):
		"""Check if there are arguments after the username mention"""
		try:
			mention = 'u/gifendore_testing' if config.is_testing_environ else 'u/gifendore'
			body = self.item.body.lower()
			if isinstance(self.item, Submission) or mention not in body or ' ' not in body:
				return 0.0
			words = body.strip().split(' ')
			for i in range(len(words)):
				if mention in words[i] and i is not len(words) - 1:
					return abs(float(words[i + 1]))
			return 0.0
		except ValueError:
			return 0.0
		except Exception as e:
			logger.exception(e)
			return 0.0

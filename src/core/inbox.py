import logging
import re
import constants
import requests
from urllib.parse import urlencode, quote
from praw.models import Comment, Submission, Message
from prawcore.exceptions import Forbidden
from praw.exceptions import APIException
from core.config import config
from core.memory import UserMemory

ISSUE_LINK = '/message/compose?to=/u/brandawg93&subject=Gifendore%20Issue&message=Please%20submit%20any%20issues%20you%20may%20have%20with%20u/gifendore%20here%20along%20with%20a%20link%20to%20the%20original%20post.'
GITHUB_LINK = 'https://github.com/Brandawg93/Gifendore'
HELP_TEXT = 'I can help you see the end of gifs that end too quickly. Simply mention my username to get the last frame.'
COMMANDS_TEXT = '\n\n**Commands:**\n\n- help: see this help message again.\n- x: replace x with any number to go back ' \
			'x seconds in the gif.\n- x-y: replace x and y with any numbers to get a smaller section of the gif.\n- ' \
			'reverse: get the gif in reverse.\n- slowmo: get the gif in slow motion.\n- freeze: freeze the end of a gif. '
logger = logging.getLogger("gifendore")


def get_commands_footer(reply_id):
	"""Get the footer text for commands."""
	edit_query = {
		'to': '/u/{}'.format(config.subreddit),
		'subject': 'Edit {}'.format(reply_id),
		'message': 'u/{} [Replace with item below]{}'.format(config.subreddit, COMMANDS_TEXT)
	}
	edit_cmd = '/message/compose?{}'.format(urlencode(edit_query, quote_via=quote))
	delete_query = {
		'to': '/u/{}'.format(config.subreddit),
		'subject': 'Delete {}'.format(reply_id),
		'message': 'Sending this will delete the bot\'s message.'
	}
	delete_cmd = '/message/compose?{}'.format(urlencode(delete_query, quote_via=quote))
	return '\n\n^[Edit]({}) ^| ^[Delete]({})'.format(edit_cmd, delete_cmd)


def get_footer():
	"""Get the footer text."""
	try:
		r = requests.get('https://botranks.com/api/getrank/gifendore')
		r.raise_for_status()
		rank = r.json()['rank']
		link = 'https://botranks.com?bot=gifendore'
		return '\n\n***\n\n^(I am a bot) ^| ^[Issues]({}) ^| [^(Rank: #{})]({}) ^| ^[Github]({})️'.format(ISSUE_LINK, rank, link, GITHUB_LINK)
	except Exception as e:
		logger.error(e)
		return '\n\n***\n\n^(I am a bot) ^| ^[Issues]({}) ^| ^[Github]({})️'.format(ISSUE_LINK, GITHUB_LINK)


class InboxItem:
	def __init__(self, item):
		"""Initialize the inbox item."""
		self.item = item
		try:
			self.marked_as_spam = item.subreddit in config.banned_subs
		except:
			self.marked_as_spam = False
		self.edit_id = None

		if item.author:
			if isinstance(item, Comment):
				self.submission = item.submission
				logger.info('{} by {} in {}'.format(item.subject, item.author.name, item.subreddit_name_prefixed))
			elif isinstance(item, Message):
				logger.info('{} by {}'.format(item.subject, item.author.name))
			elif isinstance(item, Submission):
				self.submission = item
				logger.info('submission by {} in {}'.format(item.author.name, item.subreddit))
			else:
				raise TypeError('item is not Comment or Submission')
		else:
			logger.info('Author does not exist')

	def _send_reply(self, message):
		"""Send a reply to the user."""
		response = '{}{}'.format(message, get_footer() if not self.marked_as_spam else '')
		try:
			reply = self.item.reply(response)
			if config.use_memory:
				memory = UserMemory()
				memory.add(self.item.author.name, self.item.submission.id, reply.id)
			if not self.should_send_pointers():
				commands = get_commands_footer(reply.id)
				edit_response = '{}{}{}'.format(message, commands, get_footer() if not self.marked_as_spam else '')
				reply.edit(edit_response)
			return True
		except APIException as e:
			if e.error_type == 'DELETED_COMMENT':
				logger.info('Username mention was deleted')
				return False
			raise e

	def reply_to_item(self, message, is_error=False):
		"""Send link to the user via reply."""
		if isinstance(self.item, Submission) and self.item.subreddit in [x.title for x in config.r.user.me().moderated()]:
			response = '{}{}'.format(message, get_footer() if not self.marked_as_spam else '')
			reply = self.item.reply(response)
			reply.mod.distinguish(sticky=True)
			if self.item.subreddit == 'gifendore':
				if is_error:
					self.submission.flair.select(constants.ERROR_TEMPLATE_ID)
				else:
					self.submission.flair.select(constants.SUCCESS_TEMPLATE_ID)
		else:
			og_comment = None
			if self.edit_id:
				og_comment = self.edit_id
			elif config.use_memory and not self.should_send_pointers():
				memory = UserMemory()
				og_comment = memory.get(self.item.author.name, self.item.submission.id)
			if og_comment:
				try:
					self.edit_item(og_comment, message)
				except Forbidden:
					logger.info('Comment missing. Sending a new one')
					if not self._send_reply(message):
						return
			else:
				if not self._send_reply(message):
					return
		logger.info('reply sent to {}'.format(self.item.author.name))

	def edit_item(self, og_comment, message):
		"""Edit the existing comment."""
		reply = config.r.comment(og_comment)
		commands = get_commands_footer(reply.id)
		edit_response = 'EDIT:\n\n{}{}{}'.format(message, commands, get_footer() if not self.marked_as_spam else '')
		reply.edit(edit_response)
		subject = 'Comment Edited'
		body = 'I have edited my original comment. You can find it [here]({}).{}'.format(reply.permalink, get_footer())
		self.item.author.message(subject, body)
		logger.info('Comment was edited')

	def send_help(self):
		"""Send help text to user."""
		response = '{}{}{}'.format(HELP_TEXT, COMMANDS_TEXT, get_footer() if not self.marked_as_spam else '')
		self.item.reply(response)

	def crosspost_and_pm_user(self):
		"""Crosspost to r/gifendore and message user."""
		if not self.submission.over_18:
			crosspost = self.submission.crosspost(config.subreddit, send_replies=False)
			subject = 'gifendore here!'
			body = 'Unfortunately, I am banned from r/{}. But have no fear! I have crossposted this to r/{}! You can view it [here]({}).{}'.format(self.submission.subreddit.display_name, config.subreddit, crosspost.shortlink, get_footer())
			self.item.author.message(subject, body)
			logger.info('Banned from r/{}...Crossposting for user'.format(self.submission.subreddit.display_name))

	def send_banned_msg(self):
		"""Notify user that they are banned."""
		subject = 'You have been banned from gifendore'
		body = 'Hi u/{}, Unfortunately you are banned from r/gifendore which also means you are banned from using the bot. If you have any questions, please [contact the mods.](http://www.reddit.com/message/compose?to=/r/gifendore)'.format(
			self.item.author.name)
		self.item.author.message(subject, body)
		logger.info('Banned PM sent to {}'.format(self.item.author.name))

	def should_send_pointers(self):
		"""Check if pointer easter egg should be sent."""
		return bool(re.search('^[0-9]+.*point(s)* (?:to|for).+gifendore.*', self.item.body.lower(), re.I))

	def _get_argument(self, r_text):
		"""Get the specified argument."""
		try:
			if not isinstance(self.item, Comment):
				return None
			body = re.sub('[\\[\\]\\\]', '', self.item.body)
			regex = re.compile(r_text, re.I)
			return regex.findall(body)[0]
		except IndexError:
			return None
		except Exception as e:
			logger.exception(e)
			return None

	def get_seconds(self):
		"""Get the seconds after the username or 0."""
		mention = 'u/{}'.format(config.subreddit)
		r_text = r'(?:.*){} (-?\d+[\.\d+]*)(?:.*)'.format(mention)
		return self._get_argument(r_text)

	def get_section(self):
		"""Get the section after the username or None."""
		mention = 'u/{}'.format(config.subreddit)
		r_text = r'(?:.*){} section (\d+[\.\d+]*|\*)-(\d+[\.\d+]*|\*)(?:.*)'.format(mention)
		return self._get_argument(r_text)

	def get_command(self):
		"""Get the command argument if there is one."""
		mention = 'u/{}'.format(config.subreddit)
		commands = ['slowmo', 'reverse', 'help', 'freeze']
		r_text = r'(?:.*){} ({})(?:.*)'.format(mention, '|'.join(commands))
		return self._get_argument(r_text)

	def get_message_command(self):
		"""Get the command from a PM."""
		sub_arr = self.item.subject.split(' ')
		if len(sub_arr) == 2:
			command = sub_arr[0]
			comment = sub_arr[1]
			return command.lower(), comment
		else:
			return None, None

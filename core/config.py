import json

class Config:
	def __init__(self):
		with open('core/config.json') as f:
			self.data = json.load(f)

	def get_banned_subs(self):
		return self.data['manually_included_banned_subs']

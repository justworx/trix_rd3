#
# Copyright 2018 justworx
# This file is part of the trix project, distributed under the terms 
# of the GNU Affero General Public License.
#

# UNDER CONSTRUCTION!
#  - This object may change significantly.

import re
from .. import * # trix
from . import url


class EmbedInfo(object):
	"""Find info on embeded media. (Uses https://noembed.com)"""
	
	rex_title = re.compile(b"<title.*?>(.+?)</title>")
	
	def __init__(self, tags=None):
		"""
		Pass array `tags` of keys for the desired data items. Available
		keys vary by provider. Unavailable keys are silently discarded.
		
		Default keys are: title, url, provider_name, and author_name.
		"""
		self.keys = ['title', 'url', 'provider_name', 'author_name']
	
	
	def query(self, text):
		"""
		Return text results (self.keys fields) separated by ;
		If an error occurs, an error string is generated/returned.
		If all of the above fails, an empty string is returned.
		Any python exceptions are caught and an empty string is returned.
		"""
		try:
			r = self.scan(text)
			
			# check for error
			if 'error' in r:
				ta = ['ERROR: %s' % r['error']]
				if 'url' in r:
					ta.append('; %s' % r['url'])
			
			# generate result array
			elif r:
				ta = []
				for k in self.keys:
					if k in r:
						ta.append(r[k])
			
			# generate result string
			if ta:
				return '; '.join(ta)
			
			return ''
		
		except BaseException as ex:
			return ''
		
	
	
	def scan(self, text):
		"""
		Search a line of text for the first web url and return a dict
		containing all received info.
		"""
		# see if there's an "http" or "https" link...
		if ('https://' in text) or ('http://' in text):
			
			# find link
			link = None
			words = text.split()
			for word in words:
				if (word[:8] == 'https://') or (word[:7] == 'http://'):
					link = word
			
			# find info
			if link:
				u = url.open("https://noembed.com/embed?url=%s" % link)
				r = u.reader(encoding=u.charset)
				try:
					# look for embeded video link
					return trix.jparse(r.read())
				
				except:
					# otherwise look for title
					u = url.open(link)
					r = u.reader()
					b = r.read()
					t = re.findall(self.rex_title, b)
					if t:
						t = t[0].decode(u.charset)
						return {"url":link, "title":t}
			
		# if all else fails... return empty dict
		return {}

				
			
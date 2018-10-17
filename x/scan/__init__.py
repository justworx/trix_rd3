#
# Copyright 2018 justworx
# This file is part of the trix project, distributed under
# the terms of the GNU Affero General Public License.
#

from trix.data.udata.charinfo import *
from trix.util.stream.buffer import *


class Scanner(object):
	"""Scan unicode text one character at a time."""
	
	Escape = "\\"
	BufSize = 2048
	
	#
	# default lambdas
	#
	Ident = lambda ci: (ci.cat[0]=='L') or (ci.cat=='Nd') or (ci.cat=='_')
	
	
	# NEW
	def parse(self):
		r = []
		c = self.cc
		if c.bidi == 'ON':
			if c.cat in ['Ps','Pe','Po']:
				r.append(self.parseto(c.bracket[1]))
		
		# don't forget str, int, etc here....
		
		return r
	
	
	def parseto(self, x):
		pass
		#self.parse()
		
		#
		# YOU ARE HERE
		#
	
	
	
	def __init__(self, iterable_text, **k):
		"""Pass anything iterable that produces unicode characters."""
		self.__escape = k.get('escape', self.Escape)
		self.__bufsz = k.get('bufsz', self.BufSize)
		self.__itext = iter(iterable_text)
	
	@property
	def char(self):
		"""Return the current character."""
		return self.c.c
	
	@property
	def c(self):
		"""Return current character info object."""
		try:
			return self.__cinfo
		except AttributeError:
			return self.cc
	
	@property
	def cc(self):
		"""Move forward one and return the character info object."""
		try:
			return self.__cinfo.next()
		except AttributeError:
			self.__cinfo = charinfo(self.__itext)
			return self.__cinfo.next()
	
	@property
	def bufsz(self):
		return self.__bufsz
	
	@property
	def esc(self):
		return self.__escape
	
	
	#
	# CONVENIENCE METHODS
	#
	
	# SCAN TO
	def scanto(self, c):
		"""Collect all text to the given codepoint `c`."""
		return self.collect(lambda ci: ci.c != c)
	
	# SCAN DIGITS
	def scandig(self):
		return self.collect(lambda ci: ci.dig)
	
	# SCAN IDENTIFIER
	def scanid(self):
		"""
		Collect the next sequence of characters that match the rules for 
		an "identifier". The default rules are: a letter followed by any
		number of letters, digits, or underscores (cat=='Pc').
		"""
		self.passwhite()
		if not self.c.digit:
			return self.collect(lambda ci: ci.alphanum or ci.connector)
	
	# PASS WHITE
	def passwhite(self):
		"""Pass any existing white space."""
		self.ignore(lambda ci: ci.space)
	
	
	# PASS LINE-ENDING
	def passend(self):
		"""Pass existing white space, then any endline codepoints."""
		self.passwhite()
		self.ignore(lambda c: c.lineend)
		
	
	#
	# CALLBACK-METHODS
	#  - The following methods require a callback executable to select
	#    which characters to ignore or collect.
	#
	
	# IGNORE
	def ignore(self, fn):
		"""
		Pass all characters for which executable `fn` returns True. The
		iterator stops on the first character following ignored text.
		
		NOTE: If the current character doesn't match what `fn` is looking
		      for, the pointer is not moved.
		"""
		try:
			b = fn(self.c)
			while b:
				b = fn(self.cc)
		except StopIteration:
			pass
	
	
	# COLLECT
	def collect(self, fn):
		"""
		Collect each character that matches the criteria of `fn`. The 
		pointer is left directly after the last matching character.
		"""
		b = Buffer(mode='r', max_size=self.__bufsz)
		w = b.writer()
		try:
			while fn(self.c):
				if self.c.c != self.__escape:
					w.write(self.c.c)
				else:
					w.write(self.c.cc) # it IS an escape char; get next char.
				self.cc
		except StopIteration:
			pass
		
		# read/return the whole buffer
		return b.read()

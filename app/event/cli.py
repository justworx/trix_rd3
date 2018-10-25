#
# Copyright 2018 justworx
# This file is part of the trix project, distributed under the terms 
# of the GNU Affero General Public License.
#

import ast
from . import *
from ...data.scan import *

class CLIEvent(Event):
	"""A Command-based event; Splits arguments using Scanner."""
	
	ARGPARSE = [
		lambda x: int(float(x)) if (float(x)==int(float(x))) else float(x),
		lambda x: trix.jparse(x),
		lambda x: ast.literal_eval(x),
		lambda x: str(x)
	]
	
	@classmethod
	def argparse(cls, x):
		errors = []
		for L in cls.ARGPARSE:
			try:
				return L(x)
			except Exception as ex:
				errors.append(xdata())
		
		# if all attempts to parse argument fail, raise an exception
		raise Exception("parse-fail", errors=errors)
	
	
	def __init__(self, commandline, **k):
		"""
		Pass full command line text, plus optional kwargs.
		
		This is basically just an Event created with different arguments.
		Each argument is cast as entered on `commandline`. The difference
		is that scanner is used to split arguments so JSON structures
		such as list or dict will each come out as a single argument 
		despite any internal spacing.
		
		Otherwise, it's just like Event, with the command as the first of
		`argv` and the rest of argv being individual arguments.
		"""
		
		s = Scanner(commandline)
		a = s.split()
		r = []
		try:
			for x in a:
				r.append(self.argparse(x))
			
			Event.__init__(self, *r, **k)
		
		except Exception as ex:
			raise type(ex)(xdata(line=commandline, args=a, r=r))





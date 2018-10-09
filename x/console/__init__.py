#
# Copyright 2018 justworx
# This file is part of the trix project, distributed under the terms 
# of the GNU Affero General Public License.
#

#from ..jconfig import *
#from ..event import *
from ...util.xinput import *
from ...util.enchelp import *
from ...util.linedbg import *
from ...fmt import List, Lines

from trix.app.jconfig import *
from trix.app.event import *


#
#
# CONSOLE CLASS
#
#
class Console(EncodingHelper):
	"""Base class for an interactive terminal-based user interface."""
	
	DefLang = 'en'
	DefConf = "app/console/config/%s.conf"
	
	def __init__(self, config=None, **k):
		"""
		Pass config dict keys:
		 * title    : The console's title, "Console".
		 * about    : A string with any message/description/info
		 * prompt   : If set, replaces the default command prompt
		 * messages : A dict containing message key/value pairs
		 * help     : A dict containing keywords/help messages
		 * closing  : Message to print when exiting console
		 * plugins  : A dict containing app.plugin config
		
		COMMANDS:
		 * help : print help on the specified topic
		 * exit : exit the console (returning to previous activity)
		
		EXTEND CONSOLE:
		To extend the console class, add commands (and their 'help'). 
		"""
		
		#
		# If no config is given, use a default config path. Subclasses
		# must replace DefConf with their own path.
		#
		config = config or self.DefConf % self.DefLang
		try:
			# if config is a dict, update with kwargs it and continue
			config.update(**k)
			trix.display(config)
		except AttributeError:
			# ...otherwise, config must be the inner file path to a config
			# file such as 'app/config/en.conf'.
			confile = trix.innerfpath(config)
			jconf   = JConfig(confile)
			
			# save the config
			config  = jconf.obj
		
		EncodingHelper.__init__(self, config)
		
		# debugging - store config
		self.__config = config
		
		#
		# set member variables from config
		#
		self.__title    = config.get('title', 'Console')
		self.__about    = config.get('about', 'About')
		self.__prompt   = config.get('prompt', '@app/Console')
		self.__help     = config.get('help', {})
		self.__closing  = config.get('closing', 'Closing')
		self.__messages = config.get('messages', {})
		
		pconf = config.get('plugins', {})
		self.__plugins = {}
		
		# exerimental
		self.__objects = {}
		
		perrors = {}
		for p in pconf:
			try:
				cpath = pconf[p].get("plugin")
				self.__plugins[p] = trix.create(
						cpath, p, self, pconf[p], **self.ek
					)
			except Exception as ex:
				perrors[p] = xdata(
						pluginname=p, ncreatepath=cpath, pluginconf=pconf
					)
		
		if perrors:
			raise Exception("plugin-load-errors", xdata(errors=perrors))
		
		# for display of text
		self.__lines = Lines()
		
		# prompt active
		self.__active = False
	
	
	
	@property
	def lines(self):
		return self.__lines	
	
	@property
	def title(self):
		return self.__title	
	
	@property
	def about(self):
		return self.__about	
	
	@property
	def help(self):
		return self.__help	
	
	@property
	def closing(self):
		return self.__closing	
	
	@property
	def plugins(self):
		return self.__plugins	
	
	
	@property
	def config(self):
		return self.__config
	
	
	#
	# CONSOLE - Start the console.
	#  
	def console(self):
		"""Call this method to start a console session."""
		
		try:
			self.banner()
			self.__active = True
			while self.__active:
				cmd=evt=None
				try:
					cmd = xinput(self.__prompt)
					evt = TextEvent(cmd)
					rsp = self.handle_input(evt)
					if evt.argc and evt.argv[0]:
						# Handle_input prints response; just put a blank line
						# after.
						print ('')
				
				except EOFError:
					self.__active = False
				
				except Exception as ex:
					print('') # get off the "input" line
					linedbg().dbg(self, ex.args, cmd=cmd, evt=evt.dict)
				
		except KeyboardInterrupt:
			# print a blank line so exit message won't be on the input line
			print('')
		
		# close banner
		print("%s\n" % self.closing)
	
	
	
	#
	# HANDLE INPUT
	#  - Override (and add to) these
	#
	def handle_input(self, e):
		"""Handle input event `e`."""
		
		if e.argc:
			
			# check plugins first
			for p in self.__plugins:
				self.__plugins[p].handle(e)
				if e.reply:
					self.lines.output ("%s\n" % str(e.reply))
					return
			
			# handle valid commands...
			if e.argvl[0] == 'help':
				self.handle_help(e)
			elif e.argvl[0] == 'plugins':
				self.lines.output(" ".join(self.plugins.keys()))
			elif e.argvl[0] in ['jc','conf']:
				self.handle_config (e)
			elif e.argvl[0] == 'exit':
				self.__active = False
			
			# if the first argument is blank...
			elif e.argv[0]:
				self.handle_error("invalid-command")
	
	
	"""
	# maybe later
	def _call_module(self, e):
		trix.display(e.dict)
		if e.argvl[0] == 'cq':
			if e.argc > 1:
				m = trix.nvalue('data.udata', "query")
				m(text=e.argv[1][0])
	"""		
	
	
	#
	# HANDLERS...
	#  - Add a handler for each console command you want to implement.
	#  - Override these if you need to change behavior/output.
	#
	def handle_help(self, e):
		flist = List(sep=': ', titles=sorted(self.__help.keys()))
		print (flist.format(self.__help))
	
	
	def handle_error(self, err):
		if err in self.__messages:
			print ("Error! %s" % self.__messages[err])
	
	
	def handle_config(self, e):
		
		# maybe conf is already open...
		conf = self.__objects.get("config", None)
		
		#
		# REM: argv[0] is the intenal command - the word "config", 
		#      given in the console
		#
		cmd = e.argvl[1]   # the internal command
		args = e.argvl[2:] # case-insensitive args
		Args = e.argv[2:]  # case-sensitive args
		
		if cmd in ["load","open"]:
			if conf:
				# GET THIS INTO DEBUG MESSAGES!
				self.lines(
					"""
					A config file is already open. Enter "config 
					save", then "config config" before opening a new config
					file. (If you want to discard unsaved changes, enter 
					"config reload" before "config close".)
					"""
				)
			else:
				# Use `Args[0]` (e.argv[2]) since paths are case-sensitive!
				self.__objects["config"] = JConfig(Args[0], **self.ek)
		
		elif not conf:
			# GET THIS INTO DEBUG MESSAGES!
			self.lines(
				"""
				No config file is open. Enter "config open <PATH>".
				"""
			)
		
		elif cmd in ["set","add"]:
			try:
				# rem Args[0] is the key to set/add/rmv
				Args[1] = trix.jparse(" ".join(Args[1:]))
				if cmd == 'set':
					self.__objects["config"].set(*Args)
				elif cmd == 'add':
					self.__objects["config"].add(*Args)
			except:
				raise
		
		elif cmd == 'rmv':
			self.__objects["config"].rmv(*Args)
		
		elif cmd == 'select':
			self.__objects["config"].select(*Args)
		elif cmd == 'deselect':
			self.__objects["config"].deselect()
		elif cmd == 'display':
			self.__objects["config"].display()
		elif cmd == 'show':
			self.__objects["config"].show()
		
		elif cmd == 'type':
			self.__objects["config"].type(*Args)
		elif cmd == 'keys':
			self.__objects["config"].keys(*Args)
		elif cmd in ['skeys','selkeys']:
			self.__objects["config"].keys(*Args)
		elif cmd == 'path':
			self.__objects["config"].path
		
		else:
			print ("UNKNOWN COMMAND : %s" % cmd)
			print (" -- details", trix.display(e.argv))
		
	
	
	
	
	#
	# UTILITIES...
	#
	def display(self, message):
		lines = message.splitlines()
		for line in lines:
			print (line)
	
	
	def banner(self, *a):
		self.lines.output(self.title, ff='title')
		self.lines.output(self.about, ff='about')
		print("#")
	
	
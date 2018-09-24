#
# Copyright 2018 justworx
# This file is part of the trix project, distributed under
# the terms of the GNU Affero General Public License.
#


from . import *


class IRCInfo(IRCPlugin):
	"""Info collected from various commands."""
	
	def __init__(self, pname, bot, config=None, **k):
		IRCPlugin.__init__(self, pname, bot, config, **k)
		if not self.info:
			self.info['flag'] = []
			self.info['pair'] = {}
			self.info['chan'] = {}
		
		# quicker access
		self.__channels = self.info['chan']
		
		#
		# self.channels maybe should be a dict containing info about
		# users... attributes (ops, voice, etc..)... i don't know what
		# else... notes maybe? no, that belongs in a database.
		# think about this!
		#
	
	
	@property
	def channels(self):
		"""Returns the channel info dict."""
		return self.__channels
	
	
	@property
	def prefixes(self):
		"""
		Creates (on first call) and returns (on every call) a dict that
		contains single-letter mode keys (eg, 'o', 'v', etc...) with the 
		corresponding mode-code values (eg., 
		"""
		try:
			return self.__prefixes
		except AttributeError:
			pline = self.info['pair']['PREFIX']
			
			# looking for (ov)@+
			pLpR = pline.split(")")  # split left/right of )
			pL   = pLpR[0][1:]       # start after the (
			pR   = pLpR[1]           # start after the )
			
			#
			p = {}
			for i in range(0,len(pL)):
				p[pL[i]] = pR[i]
			
			self.__prefixes = p
			return self.__prefixes
	
	
	
	def handle(self, e):
		
		if not e.argv:
			return
		
		bcmd = e.argv[0]
		
		
		# FLAGS - connect info flags
		if bcmd == 'flags':
			self.reply(e, str(self.info['flag']))
		
		
		# PAIRS - connection info keys
		elif bcmd == 'pairs':
			item = bcmd.upper()
			self.reply(e, " ".join(self.info['pair'].keys()))
		
		
		# PAIR - connection info dict
		elif bcmd == 'pair':
			if e.argc < 2:
				self.reply(e, "Keyword required. Eg, 'pair chantypes'")
			else:
				key = e.argv[1].upper()
				if key in self.info['pair']:
					self.reply(e, self.info['pair'].get(key))
		
		
		# WHO - Channel nick list
		elif bcmd == 'who':
			self.on_who(e)
			"""
			#
			# REQUIRE AUTH FOR THIS ONE!
			#
			#  - This probably needs to be moved below and put into some
			#    kind of "if" section so that it's not necessary to call 
			#    self.authorized more than once when other auth-requiring
			#    features are added.
			#  - For now, it's the only command requiring authorization, 
			#    so I'll leave it here.
			#
			if not self.authorize(e):
				return
			
			# 
			if e.argc < 1:
				self.reply(e, " ".join(self.channels.keys()))
			else:
				try:
					nicklist = " ".join(self.channels[e.argv[1]])
					self.reply(e, "%s: %s" % (e.argv[1], nicklist))
				except IndexError:
					irc.debug(e_dict=e.dict)
					self.reply(e, "No info for channel: %s" % e.argv[1])
			"""
		
		
		
		# --------------------------------------------------------------
		# PASSIVE
		#  - These are different in that they responds to irc commands
		#    rather than commands given by PRIVMSG or NOTICE.
		# --------------------------------------------------------------
		
		elif e.irccmd == 'JOIN':
			self.on_join(e)
		
		elif e.irccmd == 'KICK':
			self.on_kick(e)
		
		elif e.irccmd == 'PART':
			self.on_part(e)
		
		
		#
		# WHO
		#  - :<SERVER> 353 botix = #ai :botix @rebbot @nine
		#
		elif e.irccmd == '353':
			try:
				chan = e.argv[1]
				nlist = [e.argv[2][1:]]
				nlist.extend (e.argv[3:])
				
				# always start fresh
				self.channels[chan] = []
				
				# add each nick to the channel list
				for nick in nlist:
					
					
					# get rid of any prefix such as "@", "+", etc...
					values = self.prefixes.values()
					while nick[0] in values:
						nick = nick[1:]
					
					# add the nick to the channels list
					if nick:
						self.channels[chan].append(nick)
					
			except:
				irc.debug("info plugin: WHO (353) failed")
				raise
		
		
		#
		# SERVER INFO - 005
		#
		elif e.irccmd == '005':
			
			# data is an array now... need the first item
			data = e.text.split(':')
			data = data[0].split() # <--- split on ' ' (space)
			
			# parse each item into the correct info dict structure
			for item in data:
				x = item.split("=")
				try:
					# NAME=VALUD
					self.info['pair'][x[0]] = x[1]
				except IndexError:
					# FLAG-LIKE ITEMS
					self.info['flag'].append(x[0])
			
			# set channel types so they're directly available to the conn
			chantypes = self.info.get('pair',{}).get('CHANTYPES')
			if chantypes:
				self.bot.chantypes = chantypes
	
	
	
	#
	# EVENT HANDLERS
	#  - The code's easier for me to read when separated this way.
	#
	
	def on_who(self, e):
		if self.authorize(e):
			if e.argc < 1:
				self.reply(e, " ".join(self.channels.keys()))
			else:
				try:
					nicklist = " ".join(self.channels[e.argv[1]])
					self.reply(e, "%s: %s" % (e.argv[1], nicklist))
				except (KeyError, IndexError):
					irc.debug(e_dict=e.dict)
					self.reply(e, "No info for channel: %s" % e.argv[1])
	
	
	def on_kick(self, e):
		self.on_part(e)
		#
		# More to come here. For now, it handles the chan-list update,
		# which is what's needed immediately.
		#
	
	
	def on_part(self, e):
		try:
			if e.nick == self.bot.nick:
				del(self.channels[e.target])
			else:
				self.channels[e.target].remove(e.nick)
		except:
			irc.debug("info plugin: PART fail.", e=e.dict)
	
	
	def on_join (self, e):
		if e.nick != self.bot.nick:
			try:
				clist = self.channels[e.target]
				clist.append(e.nick)
			except:
				irc.debug("info plugin: JOIN fail.", e=e.dict)
		




#
# Copyright 2018 justworx
# This file is part of the trix project, distributed under the terms 
# of the GNU Affero General Public License.
#


from .enchelp import * # trix

DEF_SLEEP = 0.1

class Runner(EncodingHelper):
	"""Manage an event loop, start, and stop."""
	
	def __init__(self, config=None, **k):
		"""Pass config and/or kwargs."""
		
		self.__jformat = trix.ncreate('fmt.JCompact')
		self.__active = False
		self.__running = False
		self.__csock = None
		self.__cport = None
		self.__threaded = False
		self.__lineq = None
		
		
		try:
			#
			# CONFIG
			#  - If this object is part of a superclass that's already set 
			#    a self.config value, then `config` and `k` are already part
			#    or all of it.
			#
			config = self.config
		except:
			#
			#  - If not, we'll need to create the config from args/kwargs.
			#    Creating a config dict, then - regardless of whether 
			#    `config` is from an existing self.config property - update
			#    it with `k` (directly below).
			#
			config = config or {}
		
		#
		# UPDATE CONFIG WITH `k`
		#  - Runner can't take a URL parameter unless it's part of a class
		#    that converts URL (or whatever other `config` type) to a dict
		#    before calling Runner's __init__. 
		#  - Therefore... don't catch this error; let it raise immediately
		#    so the developer will know there's something wrong here.
		#  - BTW: What the developer needs to do is make sure the config
		#         passed here from a base class is given as a dict.
		#
		config.update(k)
		
		# 
		# CONFIG - COPY
		#  - Runner should work as a stand-alone class, so....
		#  - Keep a copy in case this Runner object is created as itself
		#    (rather than as a super of some other class).
		#
		self.__config = config
		
		# 
		# ENCODING HELPER
		#  - Encoding for decoding bytes received over socket connections.
		# 
		EncodingHelper.__init__(self, config)
		
		# running and communication
		self.__sleep = config.get('sleep', DEF_SLEEP)
		
		# connect to calling process
		if "CPORT" in config:
			
			#
			# moved here 20181106 (from above)
			#
			self.__lineq = trix.ncreate('util.lineq.LineQueue')
			
			
			self.__cport = p = config["CPORT"]
			self.__csock = trix.ncreate('util.sock.sockcon.sockcon', p)
			try:
				self.__csock.writeline("%i" % trix.pid())
			except Exception as ex:
				trix.log("csock-write-pid", trix.pid(), type(ex), ex.args)
		
		#
		# Create a CallIO object, which calls .io() repeatedly and works 
		# safely, either inside a thread or normally. The purpose of
		# separating this functionality is to make sure that this object
		# is destroyed even if still running in a thread at the time of
		# deletion.
		#
		self.__callio = CallIO(trix.proxify(self))
	
	
	#
	# DEL
	#
	def __del__(self):
		"""Stop. Subclasses override to implement stopping actions."""
		try:
			try:
				self.stop()
			except Exception as ex:
				trix.log(
						"err-runner-delete", "stop-fail", ex=str(ex), 
						args=ex.args, xdata=xdata()
					)
			
			if self.__csock:
				try:
					#trix.log("runner-csock", "shutdown")
					self.__csock.shutdown(SHUT_RDWR)
				except Exception as ex:
					trix.log(
							"err-runner-csock", "shutdown-fail", ex=str(ex), 
							args=ex.args, xdata=xdata()
						)
			
			if self.active:
				self.close()
		
		except BaseException as ex:
			trix.log("err-delete-ex", "shutdown-fail", ex=str(ex), 
					args=ex.args, xdata=xdata()
				)
		
		finally:
			self.__csock = None
			self.__proxy = None
	
	
	#
	# PROPERTIES
	#  - Runner is often one of a set of multiple base classes that may
	#    fail (and deconstruct) during init, so its properties need to
	#    be available even if Runner.__init__ has not yet been called.
	#  - This helps prevent raising of irrelevant Exceptions that might
	#    mask the true underlying error.
	#

	@property
	def csock(self):
		"""Used internally when opened with trix.process()."""
		try:
			return self.__csock
		except:
			self.__csock = None
			return self.__csock
	
	@property
	def config(self):
		"""The configuration dict - for reference."""
		try:
			return self.__config
		except:
			self.__config = {}
			return self.__config
	
	@property
	def active(self):
		"""True if open() has been called; False after close()."""
		return self.__active
	
	@property
	def running(self):
		"""True if running."""
		try:
			return self.__running
		except:
			self.__running = None
			return self.__running
	
	@property
	def threaded(self):
		"""True if running in a thead after call to self.start()."""
		return self.__threaded
	
	@property
	def sleep(self):
		"""Sleep time per loop."""
		try:
			return self.__sleep
		except:
			self.__sleep = DEF_SLEEP
			return self.__sleep
	
	@sleep.setter
	def sleep(self, f):
		"""Set time to sleep after each pass through the run loop."""
		self.__sleep = f
	
	
	# START
	def start(self):
		"""Run in a new thread."""
		try:
			self.__run_begin()
			trix.start(self.__callio.callio)
			self.__threaded = True
		except ReferenceError:
			self.stop()
		except Exception as ex:
			msg = "err-runner-except;"
			trix.log(msg, str(ex), ex.args, type=type(self), xdata=xdata())
			self.stop()
			raise
			
	def starts(self):
		"""Run in a new thread; returns self."""
		self.start()
		return self
	
	
	
	# OPEN
	def open(self):
		"""Called by run() if self.active is False."""
		self.__active = True
	
	
	# CLOSE
	def close(self):
		"""
		This placeholder is called on object deletion. It may be called
		anytime manually, but you should probably call .stop() first if
		the object is running. Some classes may call .close() in .stop().
		"""
		self.__active = False
	
	
	#
	# RUN
	#
	def run(self, threaded=False):
		"""Loop, calling self.io(), while self.running is True."""
		#
		# All of this exists in case Runner is running in the main thread.
		# The code must be duplicated in start/CallIO when threaded using
		# the `Runner.start` method. 
		#
		try:
			self.__run_begin()
			self.__callio.callio()
		except Exception as ex:
			msg = "Runner.run error stop;"
			trix.log(msg, str(ex), ex.args, type=type(self))
			raise
		finally:
			self.__run_end()
	
	def __run_begin(self):
		if not self.active:
			self.open()
		if self.running:
			raise Exception('already-running')
		self.__running = True
	
	def __run_end(self):
		self.__running = False
		self.__proxy = None
		self.stop()
	
	
	# IO
	def io(self):
		"""Override this method to perform repeating tasks."""
		if self.csock:
			
			# read the control socket and feed data to the line queue
			c = self.csock.read()
			self.__lineq.feed(c)
			
			# read and handle lines from controlling process
			q = self.__lineq.readline()
			while q:
				# get query response
				r = self.query(q)
				
				# package and send reply
				if not r:
					r = dict(query=q, reply=None, error='unknown-query')
				
				# write the query back to the caller
				self.csock.writeline(self.__jformat(r))
				
				# read another line (returns None when done)
				q = self.__lineq.readline()


	# QUERY
	def query(self, q):
		"""
		Answer a query from a controlling process. Responses are always
		sent as JSON dict strings.
		
		Override this method in subclasses that can run in an external
		process, adding commands your class should respond to.
		"""
		if q:
			q = q.strip()
			if q == 'ping':
				return dict(query=q, reply='pong')
			elif q == 'status':
				return dict(query=q, reply=self.status())
			elif q == 'shutdown':
				# stop, returning the new status
				self.stop()
				r = dict(query=q, reply=self.status())
				return r

	
	# STOP
	def stop(self):
		"""Stop the run loop."""
		trix.log("runner stop")
		self.__running = False
		self.__threaded = False
		self.__proxy = None
	
	# STATUS
	def status(self):
		"""Return a status dict."""
		return dict(
			ek = self.ek,
			active = self.active,
			running = self.running,
			threaded= self.threaded,
			sleep   = self.sleep,
			config  = self.config,
			cport   = self.__cport
		)
	
	# SHUTDOWN
	def shutdown(self):
		"""Stop and close."""
		with thread.allocate_lock():
			try:
				self.stop()
				self.close()
			except Exception as ex:
				msg = "Runner.shutdown error;"
				trix.log(msg, str(ex), ex.args, type=type(self))
				raise
	
	
	def on_interrupt(self):
		pass
	
	
	# DISPLAY
	def display(self):
		"""Print status."""
		trix.display(self.status())





class CallIO(object):
	"""
	Runner can't call trix.start to start or it won't stop unless 
	specifically told to (by calling, for example, `myrunner.stop()`.
	Use a CallIO object to call io() just as Runner.run would but from
	within a thread that holds its link to the Runner object by proxy.
	Then, when the object is destroyed in the main thread, it will no
	longer remain in the alternate thread.
	"""
	def __init__(self, runner):
		self.__runner = trix.proxify(runner)
	
	def callio(self):
		try:
			while self.__runner.running:
				try:
					self.__runner.io()
					time.sleep(self.__runner.sleep)
				except KeyboardInterrupt:
					self.__runner.on_interrupt()
		
		except ReferenceError:
			pass





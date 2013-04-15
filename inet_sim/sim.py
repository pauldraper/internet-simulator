import sched

class Scheduler:
	"""Schedules events for the simulator."""

	def __init__(self):
		"""Create an empty scheduler."""
		self.current = 0
		self.scheduler = sched.scheduler(self.get_time, self.advance_time)
	
	def get_time(self):
		"""Return current time of Scheduler."""
		return self.current

	def advance_time(self, units):
		"""Advance time in the Scheduler by the given number of units."""
		self.current += units

	def add(self, handler, args=(), delay=0, priority=1):
		"""Schedule a function call."""
		return self.scheduler.enter(delay, priority, handler, args)
	
	def cancel(self, event):
		self.scheduler.cancel(event)

	def cancel_all(self):
		"""Cancel all scheduled events."""
		map(self.scheduler.cancel, self.scheduler.queue)
	
	def run(self):
		self.scheduler.run()

class _SleepException(Exception):
	"""Thrown when sleep is needed."""
	def __init__(self, timeout):
		self.timeout = timeout	
def sleep(timeout):
	"""Sleep for timeout."""
	raise _SleepException(timeout)
	yield


class _WaitException(Exception):
	"""Thrown when wait is needed."""
	def __init__(self, lock, timeout):
		self.lock = lock
		self.timeout = timeout
def wait(lock, timeout=None):
	raise _WaitException(lock, timeout)
	yield
	
class _ResumeException(Exception):
	"""Thrown when wait is needed."""
	def __init__(self, lock, args):
		self.lock = lock
		self.args = args
def resume(lock, *args):
	raise _ResumeException(lock, args)
	yield

class _GetStackException(Exception):
	pass
def get_stack():
	raise _GetStackException()
	yield
	
class TimeoutException(Exception):
	"""Thrown when timed out."""
	pass
def attempt(f, attempts):
	"""Attempt multiple times."""
	for _ in range(attempts):
		try:
			ret((yield f()))
		except TimeoutException:
			pass
	raise TimeoutException

class _ReturnValue(Exception):
	def __init__(self, value):
		self.value = value
def ret(value):
	raise _ReturnValue(value)

class Lock:
	def __init__(self, start_time):
		self._waiting = []
		self._last_released = start_time

class Simulator:
	"""Controls function calls and flow."""
	
	def __init__(self):
		"""Creates a new Simulator."""
		self.scheduler = Scheduler()
	
	def create_lock(self):
		"""Create a lock for use in wait() and resume()."""
		return Lock(self.scheduler.get_time())
	
	def new_thread(self, gen):
		"""Add a new thread."""
		self.__proceed([gen])
		return gen
		
	def run(self):
		"""Run the simulator to completion."""
		self.scheduler.run()
	
	def __proceed(self, stack, action=lambda c: c.send(None)):
		"""Perform next call."""
		if not stack:
			return
		try:
			next_call = action(stack[-1])
		except StopIteration as e:
			stack.pop()
			self.__proceed(stack, lambda c: c.send(None))
		except _ReturnValue as e:
			stack.pop()
			self.__proceed(stack, lambda c: c.send(e.value))
		except _SleepException as e:
			stack.pop()
			self.scheduler.add(self.__proceed, (stack,), e.timeout)
		except _WaitException as e:
			stack.pop()
			e.lock._waiting.append(stack)
			if e.timeout is not None:
				def timed_out(e=e, start_time=self.scheduler.get_time()):
					if start_time >= e.lock._last_released:
						e.lock._waiting.remove(stack)
						self.__proceed(stack, lambda c: c.throw(TimeoutException))
				self.scheduler.add(timed_out, delay=e.timeout)
		except _ResumeException as e:
			stack.pop()
			stacks, e.lock._waiting = e.lock._waiting, []
			e.lock._last_released = self.scheduler.get_time()
			for s in stacks:
				self.__proceed(s, lambda c: c.send(e.args))
			self.__proceed(stack, lambda c: c.send(None))
		except _GetStackException as e:
			stack.pop()
			self.__proceed(stack, lambda c: c.send(stack))
		except BaseException as e: #change to Exception? (but then what about Generator exit?)
			stack.pop()
			self.__proceed(stack, lambda c: c.throw(e))
		else:
			stack.append(next_call)
			self.__proceed(stack)

simulator = Simulator() #singleton

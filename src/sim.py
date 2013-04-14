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
	return #In Python 3.3, simply use `yield from iter(())`
	yield

class _WaitException(Exception):
	"""Thrown when wait is needed."""
	def __init__(self, lock, timeout):
		self.lock = lock
		self.timeout = timeout
def wait(lock, timeout=None):
	raise _WaitException(lock, timeout)
	return #In Python 3.3, simply use `yield from iter(())`
	yield
	
class _ResumeException(Exception):
	"""Thrown when wait is needed."""
	def __init__(self, lock, args):
		self.lock = lock
		self.args = args
def resume(lock, *args):
	raise _ResumeException(lock, args)
	return #In Python 3.3, simply use `yield from iter(())`
	yield
	
class TimeoutException(Exception):
	"""Thrown when timed out."""
	pass
def attempt(f, attempts):
	"""Attempt multiple times."""
	for _ in range(attempts):
		try:
			return (yield f())
		except TimeoutException:
			pass
	raise TimeoutException

class Simulator:
	"""Controls function calls and flow."""

	def __init__(self):
		"""Creates a new Simulator."""
		self.scheduler = Scheduler()
	
	def create_lock(self):
		class Lock:
			def __init__(self, start_time):
				self.waiting = []
				self.last_released = start_time
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
			self.__proceed(stack, lambda c: c.send(e.value))
		except _SleepException as e:
			self.scheduler.add(self.__proceed, (stack,), e.timeout)
		except _WaitException as e:
			stack.pop()
			e.lock.waiting.append(stack)
			if e.timeout is not None:
				start_time = self.scheduler.get_time()
				def timed_out(e=e):
					if start_time >= e.lock.last_released:
						self.__proceed(stack, lambda c: c.throw(TimeoutException))
				self.scheduler.add(timed_out, delay=e.timeout)
		except _ResumeException as e:
			stacks, e.lock.waiting = e.lock.waiting, []
			e.lock.last_released = self.scheduler.get_time()
			for stack in stacks:
				self.__proceed(stack, lambda c: c.send(e.args))
		else:
			stack.append(next_call)
			self.__proceed(stack)

simulator = Simulator() #singleton

class Logger:
	"""Logs messages."""

	def __init__(self, level=1):
		"""Creates a new logger."""
		self.level = level

	def log(self, text, level=1):
		"""Log a message with the given level."""
		if level <= self.level:
			print('{:10.4f} {}'.format(simulator.scheduler.get_time(), text))

logger = Logger() #singleton
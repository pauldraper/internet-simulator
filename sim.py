from datetime import datetime, timedelta
import random
import sched

class Scheduler:
	 """Schedules events for the simulator."""

	def __init__(self):
		"""Create an empty scheduler."""
		self.current = 0
		self.scheduler = sched.scheduler(self.get_time,self.advance_time)
	
	def get_time(self):
		"""Return current time of Scheduler."""
		return self.current

	def advance_time(self, units):
		"""Advance time in the Scheduler by the given number of units."""
		self.current += units

	def add(self, handler, args=(), delay=0, priority=1):
		"""Schedule a function call."""
		return self.scheduler.enter(delay, priority, handler, args)

	def cancel_all(self):
		"""Cancel all scheduled events."""
		map(self.scheduler.cancel, self.scheduler.queue)

	def run(self, duration=None):
		"""Run scheduled events."""
		self.start_time = datetime.now()
		if duration is not None:
			self.scheduler.enter(duration, 0, self.cancel_all, [])
		self.scheduler.run()

scheduler = Scheduler() #singleton


class Generator:
	"""Generates repeated events."""

	def __init__(self, avg_delay, duration, next=(lambda event,args: (event,args))):
		"""Create new Generator with the given parameters."""
		self.next = next
		self.avg_delay = avg_delay
		self.end_time = duration + scheduler.get_time()

	def generate(self, event, args):
		"""Generate events."""
		delay = random.expovariate(1./self.avg_delay)
		if delay + scheduler.get_time() >= self.end_time:
			return
		scheduler.add(event, args, delay)
		scheduler.add(self.generate, list(self.next(event, args)), delay)

	
class Logger:
	"""Logs messages."""

	def __init__(self, level=1):
		"""Creates a new logger."""
		self.level = level

	def log(self, text, level=1):
		"""Log a message with the given level."""
		if level <= self.level:
			print '%15f %s' % (scheduler.get_time(), text)

logger = Logger() #singleton

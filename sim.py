from datetime import datetime, timedelta
import random
import sched

class Scheduler:

	def __init__(self):
		self.current = 0
		self.scheduler = sched.scheduler(self.get_time,self.advance_time)
	
	def get_time(self):
		return self.current

	def get_realtime(self):
		return self.start_time + timedelta(seconds=self.current)

	def advance_time(self, units):
		self.current += units

	def add(self, handler, args=(), delay=0, priority=1):
	   return self.scheduler.enter(delay, priority, handler, args)

	def cancel_all(self):
		map(self.scheduler.cancel, self.scheduler.queue)

	def run(self, duration=None):
		self.start_time = datetime.now()
		if duration is not None:
			self.scheduler.enter(duration, 0, self.cancel_all, [])
		self.scheduler.run()

scheduler = Scheduler()

class Generator:
	def __init__(self, avg_delay, duration, next=(lambda event,args: (event,args))):
		self.next = next
		self.avg_delay = avg_delay
		self.end_time = duration + scheduler.get_time()

	def generate(self, event, args):
		delay = random.expovariate(1./self.avg_delay)
		if delay + scheduler.get_time() >= self.end_time:
			return
		scheduler.add(event, args, delay)
		scheduler.add(self.generate, list(self.next(event, args)), delay)
		
class Logger:
	def __init__(self):
		self.level = 1

	def log(self, text, level=1):
		if level <= self.level:
			print '%15f %s' % (scheduler.get_time(), text)

logger = Logger()

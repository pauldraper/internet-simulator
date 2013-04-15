from inet_sim.sim import simulator

class Logger:
	"""Logs messages."""

	def __init__(self, current_time, level=1):
		"""Creates a new logger."""
		self.current_time = current_time
		self.level = level

	def log(self, text, level=1):
		"""Log a message with the given level."""
		if level <= self.level:
			print('{:10.4f} {}'.format(simulator.scheduler.get_time(), text))

logger = Logger(simulator.scheduler.get_time) #singleton
from collections import namedtuple

Event = namedtuple('Event', 'time name args')

class EventParser:
	def __init__(self, file_path):
			""" Initialize plotter with a file name. """
			self.file_path = file_path
	
	def parse(self):
		""" Parse the data file """
		file = open(self.file_path)
		try:
			for line in file:
				if line.startswith("#"):
					continue
				fields = line.split()
				yield Event(time=float(fields[0]), name=fields[1], args=tuple(fields[2:]))
		finally:
			file.close()
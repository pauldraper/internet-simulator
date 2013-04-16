import argparse
import string

import matplotlib
from pylab import *

from .parse import EventParser

class QueuePlotter:
	"""Parses a file of queue events and plots a graph over time."""

	def load(self, parser):
		"""Load data from the parser."""
		sizes = []
		drops = []
		size = 0
		for event in parser.parse():
			if event.name == 'queue-start' and event.args[0] == '3':
				size += 1
				sizes.append((event.time, size))
			elif event.name == 'queue-end' and event.args[0] == '3':
				size -= 1
				sizes.append((event.time, size))
			elif event.name == 'queue-overflow' and event.args[0] == '3':
				drops.append((event.time, size+1))
		self.sizes = sizes
		self.drops = drops

	def plot(self, file_path, max_queue):
		"""Create and save the graph."""
		if not hasattr(self, 'sizes') or not hasattr(self, 'drops'):
			raise Exception('nothing loaded, please load() first')
		clf()
		x, y = [], []
		for time, size in self.sizes:
			x.append(time)
			y.append(size)
		drop_x, drop_y = [], []
		for time, size in self.drops:
			drop_x.append(time)
			drop_y.append(size)
		plot(x,y)
		scatter(drop_x, drop_y, marker='x', color='black')
		xlabel('Time (seconds)')
		ylabel('Queue Size (packets)')
		xlim([min(x), max(x)])
		ylim([0, max(y)+2])
		savefig(file_path)

def _parse_args():
		parser = argparse.ArgumentParser(description='Plot queue size over time')
		parser.add_argument('-i', '--input' , dest='input_file', help='input file')
		parser.add_argument('-o', '--output' , dest='output_file', help='output file')
		return parser.parse_args()

if __name__ == '__main__':
	args = _parse_args()
	p = QueuePlotter()
	p.load(EventParser(args.input_file))
	p.plot(args.output_file, 15)

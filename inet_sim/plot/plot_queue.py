import itertools
import argparse
import string

import matplotlib
from pylab import *

from plot_parse import EventParser

class QueuePlotter:
	"""Parses a file of queue events and plots a graph over time."""

	def load(self, parser):
		"""Load data from the parser."""
		sizes = []
		drops = []
		size = 0
		for event in parser.parse():
			if event.name == 'queue-start':
				size += 1
				sizes.append((event.time, size))
			elif event.name == 'queue-end':
				size -= 1
				sizes.append((event.time, size))
			elif event.name == 'queue-overflow':
				drops.append((event.time, size))
		self.sizes = sizes
		self.drops = drops

	def save(self, file_path, max_queue):
		"""Create and save a graph."""
		if not hasattr(self, 'sizes') or not hasattr(self, 'drops'):
			raise Exception('nothing loaded, please load() first')
		
		clf()
		x, y = [], []
		drop_x, drop_y = [], []
		max = None
		for time, size in self.data:
			if size == 'x':
				dropX.append(time)
				dropY.append(size)
			else:
				x.append(time)
				y.append(size)

		plot(x,y)
		scatter(dropX, dropY, marker='x', color='black')
		xlabel('Time (sseconds)')
		ylabel('Queue Size (packets)')
		min_time = min(time for time,size in itertools.chain(self.data, self.drops))
		max_time = max(time for time,size in itertools.chain(self.data, self.drops))
		xlim([min_time, max_time])
		ylim([0,max_queue+2])
		savefig(file_path)

def _parse_args():
		parser = argparse.ArgumentParser(description='Plot queue size over time')
		parser.add_argument('-i', '--input' , type=string, dest='input_file', help='input file')
		parser.add_argument('-o', '--output' , type=string, dest='output_file', help='output file')
		return parser.parse_args()

if __name__ == '__main__':
	args = _parse_args()
	p = QueuePlotter()
	p.parse(EventParser(args.input_file))
	p.plot(args.output_file)

import argparse
from collections import deque
import string

import matplotlib
from pylab import *

from ..parse import EventParser

# Class that parses a file of rates and plots a smoothed graph
class RatePlotter:
	"""Plots a graph of smooted transfer rates."""

	def parse(self, parser):
		"""Load data from the parser."""
		data = []
		for event in parser.parse():
			if event.name == 'tcp-send' and event.args[2] == 'data':
				start, end = map(int, event.args[3].split('-'))
				data.append((event.time, end-start+1))
		self.data = data

	def plot(self, file_path):
		"""Create and save the graph."""
		if not hasattr(self, 'data'):
			raise Exception('nothing loaded, please load() first')
		clf()
		x = []
		y = []
		total_size = 0
		sizes = deque()
		for time, size in self.data:
			while sizes and sizes[:-1] < time - .1:
				total_size -= sizes.pop()
			sizes.appendleft(size)
			total_size += size
			x.append(time)
			y.append(total_size / len(sizes) * 8 / 10e6)
		plot(x,y)
		xlabel('Time (seconds)')
		ylabel('Rate (Mbps)')
		xlim([min(x), max(y)])
		ylim([0, max(y)+2])
		savefig(file_path)

def _parse_args():
		parser = argparse.ArgumentParser(description='Plot queue size over time')
		parser.add_argument('-i', '--input' , type=string, dest='input_file', help='input file')
		parser.add_argument('-o', '--output' , type=string, dest='output_file', help='output file')
		return parser.parse_args()

if __name__ == '__main__':
	(options,args) = _parse_args()
	p = RatePlotter()
	p.parse(EventParser(args.input_file))
	p.plot(args.output_file)

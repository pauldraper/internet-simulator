from __future__ import division
import argparse

import matplotlib
from pylab import *

from .parse import EventParser

# Class that parses a file of rates and plots a smoothed graph
class WindowPlotter:
	"""Plots a graph of cwnd and ssthresh."""

	def load(self, parser, ip_port):
		"""Load data from the parser."""
		self.cwnd = [(0,1500)]
		self.ssthresh = [(0,9600)]
		for event in parser.parse():
			if event.name == 'tcp-cwnd-adjust' and event.args[0] == ip_port:
				self.cwnd.append((event.time, int(event.args[1])))
			elif event.name == 'tcp-ssthresh-adjust' and event.args[0] == ip_port:
				self.ssthresh.append((event.time, int(event.args[1])))

	def plot(self, file_path):
		"""Create and save the graph."""
		if not hasattr(self, 'cwnd') or not hasattr(self, 'ssthresh'):
			raise Exception('nothing loaded, please load() first')
		clf()
		cwnd_xy = zip(*self.cwnd)
		ssthresh_xy = zip(*self.ssthresh)
		plot(cwnd_xy[0], cwnd_xy[1])
		plot(ssthresh_xy[0], ssthresh_xy[1], c='g')
		xlabel('Time')
		ylabel('Value')
		xlim([0, 1.1*max(cwnd_xy[0] + ssthresh_xy[0])])
		ylim([0, 100000])
		savefig(file_path)

def _parse_args():
		parser = argparse.ArgumentParser(description='Plot queue size over time')
		parser.add_argument('-i', '--input' , dest='input_file', help='input file')
		parser.add_argument('-o', '--output' , dest='output_file', help='output file')
		return parser.parse_args()

if __name__ == '__main__':
	args = _parse_args()
	p = WindowPlotter()
	p.load(EventParser(args.input_file), '101.0.0.0:81')
	p.plot(args.output_file)

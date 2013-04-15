import argparse
import string

import matplotlib
from pylab import *

from ..parse import EventParser

class SequencePlotter:
	"""Plots a graph of sequence numbers."""

	def parse(self, parser, ip_port):
		"""Load data from the parser."""
		sends = []
		acks = []
		for event in parser.parse():
			if event.name == 'tcp-send' and event.args[0] == ip_port and event.args[2] == 'data':
				end = int(event.args[3].split('-')[1])
				acks.append((event.time, end+1))
			if event.name == 'tcp-recv' and event.args[0] == ip_port and event.args[2] == 'ack':
				acks.append((event.time, int(event.args[3])))
		self.sends = sends
		self.acks = acks

	def plot(self, file_path):
		""" Create and save the graph."""
		if not hasattr(self, 'sends') or not hasattr(self, 'acks'):
			raise Exception('nothing loaded, please load() first')
		clf()
		figure(figsize=(15,5))
		x, y = [], []
		ackX, ackY = [], []
		for time, seq in self.sends:
			x.append(time)
			y.append(seq % 75000)
		for time, seq in self.acks:
			ackX.append(time)
			ackY.append(seq % 75000)
		scatter(x, y, marker='s', s=3)
		scatter(ackX, ackY, marker='s', s=0.2)
		xlabel('Time (seconds)')
		ylabel('Sequence Number Mod 75000')
		xlim([self.min_time,self.max_time])
		savefig(file_path)

def _parse_args():
		parser = argparse.ArgumentParser(description='Plot queue size over time')
		parser.add_argument('-i', '--input' , type=string, dest='input_file', help='input file')
		parser.add_argument('-o', '--output' , type=string, dest='output_file', help='output file')
		return parser.parse_args()

if __name__ == '__main__':
	args = _parse_args()
	p = SequencePlotter()
	p.parse(EventParser(args.input_file))
	p.plot(args.output_file)

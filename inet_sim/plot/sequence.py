import argparse

import matplotlib
from pylab import *

from inet_sim.plot.parse import EventParser

class SequencePlotter:
	"""Plots a graph of sequence numbers."""

	def parse(self, parser, ip_port):
		"""Load data from the parser."""
		sends = []
		acks = []
		for event in parser.parse():
			if event.name == 'tcp-send' and event.args[0] == ip_port and event.args[2] == 'data':
				end = int(event.args[3].split('-')[1]) + 1
				sends.append((event.time, end))
			elif event.name == 'tcp-recv' and event.args[0] == ip_port and event.args[2] == 'ack':
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
			y.append(seq % 200000)
		for time, seq in self.acks:
			ackX.append(time)
			ackY.append(seq % 200000)
		scatter(x, y, marker='o', s=7, linewidths=(0.,))
		scatter(ackX, ackY, marker='+', c='g', s=9)
		xlabel('Time (seconds)')
		ylabel('Sequence Number Mod 200000')
		xlim([0, max(x)])
		ylim([0, 200000])
		savefig(file_path)

def _parse_args():
		parser = argparse.ArgumentParser(description='Plot queue size over time')
		parser.add_argument('-i', '--input' , dest='input_file', help='input file')
		parser.add_argument('-o', '--output' , dest='output_file', help='output file')
		return parser.parse_args()

if __name__ == '__main__':
	args = _parse_args()
	p = SequencePlotter()
	p.parse(EventParser(args.input_file), '101.0.0.0:80')
	p.plot(args.output_file)

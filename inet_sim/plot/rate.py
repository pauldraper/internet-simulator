from __future__ import division
import argparse
from collections import deque
import string

import matplotlib
from pylab import *

from .parse import EventParser

# Class that parses a file of rates and plots a smoothed graph
class RatePlotter:
	"""Plots a graph of smooted transfer rates."""

	def load(self, parser, ip_port):
		"""Load data from the parser."""
		data = []
		ack_num = 0
		for event in parser.parse():
			if event.name == 'tcp-send' and event.args[0] == ip_port and event.args[2] == 'ack':
				ack_num = max(ack_num, int(event.args[3]))
			if event.name == 'tcp-recv' and event.args[0] == ip_port and event.args[2] == 'data':
				start, end = map(int, event.args[3].split('-'))
				if start >= ack_num:
					data.append((event.time, end-start+1))
		x = [0]
		y = [0]
		total = 0
		i, j = 0, 0
		for t in xrange(0, 1*int(data[-1][0])):
			time = t / 1
			while data[i][0] < time - 20:
				total -= data[i][1]
				i += 1
			while data[j][0] < time:
				total += data[j][1]
				j += 1
			x.append(time)
			y.append(total * 8 / 10e3 / 20)
		return x, y

	def plot(self, input_file, file_path, *ip_ports):
		"""Create and save the graph."""
		clf()
		colors = ['g','b','r','y','m']
		parser = EventParser(args.input_file)
		mx, mn = 0, 10e9
		for i, ip_port in enumerate(ip_ports): 
			x, y = self.load(parser, ip_port)
			#mx = max(mx, max(x))
			plot(x, y, c=colors[i])
		xlabel('Time (seconds)')
		ylabel('Rate (Kbps)')
		xlim([0, max(x)])
		#ylim([0, max(y)])
		print max(y)
		savefig(file_path)

def _parse_args():
		parser = argparse.ArgumentParser(description='Plot queue size over time')
		parser.add_argument('-i', '--input' , dest='input_file', help='input file')
		parser.add_argument('-o', '--output' , dest='output_file', help='output file')
		return parser.parse_args()

if __name__ == '__main__':
	args = _parse_args()
	p = RatePlotter()
	p.plot(args.input_file, args.output_file, '123.0.0.0:32768', '123.0.0.0:32769', '123.0.0.0:32770')

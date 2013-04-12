from __future__ import division
import random

from collections import deque
from sim import scheduler, logger

log = lambda x: logger.log(x, 3)

class Packet:
	id_counter = 0

	def __init__(self, protocol, origin, dest, message):
		self.protocol = protocol
		self.origin = origin
		self.dest = dest
		self.message = message
		self.id = Packet.id_counter
		Packet.id_counter += 1

	@property
	def size(self):
		return (len(self.message) if self.message else 0) + 4

class Link: #(unidirectional)
	id_counter = 0

	def __init__(self, source, dest, prop_delay, bandwidth):
		source.links.append(self)
		self.dest = dest
		self.prop_delay = prop_delay
		self.bandwidth = bandwidth
		self.busy = False
		self.queue = deque()
		self.id = Link.id_counter
		self.loss = 0
		self.reorder = 0
		Link.id_counter += 1

	def enqueue(self, packet):
		if random.random() < self.loss:
			log('packet-loss %d %d' % (self.id, packet.id))
		else:
			log('queue-start %d %d' % (self.id, packet.id))
			if self.busy:
				self.queue.appendleft(packet)
			else:
				self.transmit(packet)

	def transmit(self, packet):
		log('queue-end %d %d' % (self.id, packet.id), )
		log('transmit-start %d %d' % (self.id, packet.id), )
		self.busy = True
		scheduler.add(self.propogate, [packet], packet.size/self.bandwidth)

	def propogate(self, packet):
		log('transmit-end %d %d' % (self.id, packet.id), )
		log('propogate-start %d %d' % (self.id, packet.id), )
		scheduler.add(self.arrive, [packet], self.prop_delay)
		self.busy = False
		if self.queue:
			self.transmit(self.queue.pop())

	def arrive(self, packet):
		log('propogate-end %d %d' % (self.id, packet.id), )
		self.dest.received(packet)

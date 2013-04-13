from __future__ import division
from collections import deque
import random

from sim import scheduler, logger

log = lambda x: logger.log(x, 3)

class Packet:
	"""Represents a transport-level packet."""
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

class Link:
	"""Represents a unidirectional link."""

	id_counter = 0

	def __init__(self, source, dest, prop_delay, bandwidth):
		"""Creates a Link between the specified Hosts, that has the given performance.
		(This also adds the Link to the source Host's outgoing links.)"""
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
		"""Called to place this packet in the queue."""
		if random.random() < self.loss:
			log('packet-loss %d %d' % (self.id, packet.id))
		else:
			log('queue-start %d %d' % (self.id, packet.id))
			if self.busy:
				self.queue.appendleft(packet)
			else:
				self.__transmit(packet)

	def __transmit(self, packet):
		"""Begin packet transmission (and schedule propogation)."""
		log('queue-end %d %d' % (self.id, packet.id), )
		log('__transmit-start %d %d' % (self.id, packet.id), )
		self.busy = True
		scheduler.add(self.__propogate, [packet], packet.size/self.bandwidth)

	def __propogate(self, packet):
		"""Begin packet propogation (and schedule tranmission)."""
		log('__transmit-end %d %d' % (self.id, packet.id), )
		log('__propogate-start %d %d' % (self.id, packet.id), )
		scheduler.add(self.__arrive, [packet], self.prop_delay)
		self.busy = False
		if self.queue:
			self.__transmit(self.queue.pop())

	def __arrive(self, packet):
		"""Delivery packet to destination Host."""
		log('__propogate-end %d %d' % (self.id, packet.id), )
		self.dest.received(packet)

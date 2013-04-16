from __future__ import division
from collections import deque
import random

from ..log import logger
from ..sim import simulator, sleep

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
		self.max_queue_size = 24
		self.id = Link.id_counter
		self.loss = 0
		self.reorder = 0
		Link.id_counter += 1

	def enqueue(self, packet):
		"""Called to place this packet in the queue."""
		if self.max_queue_size is not None and self.max_queue_size <= len(self.queue):
			log('queue-overflow %d %d' % (self.id, packet.id))
		elif random.random() < self.loss:
			log('packet-loss %d %d' % (self.id, packet.id))
		else:
			log('queue-start %d %d' % (self.id, packet.id))
			self.queue.appendleft(packet)
			if not self.busy:
				simulator.new_thread(self.__transmit())

	def __transmit(self):
		"""Transmit packet."""
		packet = self.queue.pop()
		log('queue-end %d %d' % (self.id, packet.id))
		
		log('transmit-start %d %d' % (self.id, packet.id))
		self.busy = True
		yield sleep(packet.size / self.bandwidth)
		log('transmit-end %d %d' % (self.id, packet.id))
		
		self.busy = False
		if self.queue:
			simulator.new_thread(self.__transmit())
		
		log('propogate-start %d %d' % (self.id, packet.id))
		yield sleep(self.prop_delay)
		log('propogate-end %d %d' % (self.id, packet.id))
		
		yield self.dest.received(packet)

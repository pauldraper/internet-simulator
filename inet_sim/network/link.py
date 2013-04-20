from __future__ import division
import heapq
import itertools
import logging
import random

from sim import sim, Mutex

class IpPacket:
	"""Represents a network packet."""
	
	id_counter = itertools.count()

	def __init__(self, origin, dest, body):
		"""Create a IpPacket."""
		self.id = next(IpPacket.id_counter)
		self.origin = origin
		self.dest = dest
		self.body = body

	def __len__(self):
		"""Return the size, in bytes."""
		return len(self.body) if self.body else 0
			
class Link:
	"""Represents a unidirectional link."""

	id_counter = itertools.count()

	@staticmethod
	def duplex_link(node1, node2, prop_delay, bandwidth):
		link1 = Link(node1, node2, prop_delay, bandwidth)
		link2 = Link(node2, node1, prop_delay, bandwidth)
		node1.add_link(link1, link2)
		node2.add_link(link2, link1)
		return link1, link2

	def __init__(self, source, dest, prop_delay, bandwidth):
		"""Creates a Link between the specified Hosts.
		This also registers the Link with the source."""
		self.source = source
		self.dest = dest
		self.prop_delay = prop_delay
		self.bandwidth = bandwidth
		self.id = next(Link.id_counter)
		self.loss = 0.
		
		self.__max_queue_size = 48
		self.__queue = []
		self.__mutex = Mutex()
		
	
	def __log(self, fmt, *args):
		logging.getLogger(__name__).info('link %s->%s '+fmt, self.source.ip, self.dest.ip, *args)

	def enqueue(self, packet, priority=3):
		"""Called to place this packet in the queue."""
		if random.random() < self.loss:
			self.__log('packet-loss %d', packet.id)
		elif len(self.__queue) >= self.__max_queue_size:
			self.__log('queue-overflow %d', packet.id)
		else:
			heapq.heappush(self.__queue, (priority, packet))
			self.__log('queue-start %d', packet.id)
			sim.new_thread(self.send)
			
	def send(self):
		self.__mutex.lock()
		priority, packet = heapq.heappop(self.__queue)
		self.__log('queue-end %d', packet.id)
		
		self.__log('transmit-start %d', packet.id)
		sim.sleep(len(packet) / self.bandwidth)
		self.__log('transmit-end %d', packet.id)
		self.__mutex.unlock()
		
		self.__log('propogate-start %d', packet.id)
		sim.sleep(self.prop_delay)
		self.__log('propogate-end %d', packet.id)
		self.dest.received(packet, self)


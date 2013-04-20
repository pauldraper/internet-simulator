from __future__ import division
import itertools
import logging
import random

from sim import sim, Mutex

class Packet:
	"""Represents a network packet."""
	
	id_counter = itertools.count()

	def __init__(self, origin, dest, message):
		"""Create a Packet."""
		self.id = next(Packet.id_counter)
		self.origin = origin
		self.dest = dest
		self.message = message

	@property
	def size(self):
		"""Return the size, in bytes."""
		return len(self.message) if self.message else 0
			
class Link:
	"""Represents a unidirectional link."""

	id_counter = itertools.count()

	def __init__(self, source, dest, prop_delay, bandwidth):
		"""Creates a Link between the specified Hosts.
		This also registers the Link with the source."""
		self.source = source
		self.dest = dest
		source.routing[dest.ip] = self
		self.prop_delay = prop_delay
		self.bandwidth = bandwidth
		self.id = next(Link.id_counter)
		self.loss = 0.
		#self.reorder = 0.
		self.__available_queue = 48
		self.__mutex = Mutex()
		
	
	def __log(self, fmt, *args):
		logging.getLogger(__name__).info('link %s->%s '+fmt, self.source.ip, self.dest.ip, *args)

	def enqueue(self, packet):
		"""Called to place this packet in the queue."""
		if random.random() < self.loss:
			self.__log('packet-loss %d', packet.id)
		elif self.__available_queue <= 0:
			self.__log('queue-overflow %d', packet.id)
		else:
			self.__available_queue -= 1
			self.__log('queue-start %d', packet.id)
			def send():
				self.__mutex.lock()
				self.__log('queue-end %d', packet.id)
				self.__available_queue += 1
				
				self.__log('transmit-start %d', packet.id)
				sim.sleep(packet.size / self.bandwidth)
				self.__log('transmit-end %d', packet.id)
				self.__mutex.unlock()
				
				self.__log('propogate-start %d', packet.id)
				sim.sleep(self.prop_delay)
				self.__log('propogate-end %d', packet.id)
				self.dest.received(packet)
			sim.new_thread(send)


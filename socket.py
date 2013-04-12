from abc import ABCMeta, abstractmethod
from collections import deque

from link import Packet
from sim import scheduler, logger

log = lambda x: logger.log(x, 2)

class Socket:
	__metaclass__ = ABCMeta

	def __init__(self, host):
		self.host = host

	def schedule_send(self, packet):
		self.host.getLinks(packet.dest[0]).next().enqueue(packet)

	@abstractmethod
	def _buffer(self, packet):
		pass

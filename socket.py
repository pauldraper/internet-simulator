from abc import ABCMeta, abstractmethod

from sim import logger

log = lambda x: logger.log(x, 2)

class Socket:
	"""Base class for sockets."""

	__metaclass__ = ABCMeta

	def __init__(self, host):
		"""Create a socket, with the given host."""
		self.host = host

	def sched_send(self, packet):
		"""Enqueue the given Packet on the correct outbound Link, depending on the Packet's
		destination address.
		"""
		next(self.host.get_links(packet.dest[0])).enqueue(packet)

	@abstractmethod
	def _buffer(self, packet):
		"""Called by the Host to pass a packet to this Socket."""
		pass

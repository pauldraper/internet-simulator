from abc import ABCMeta, abstractmethod
import logging

class Socket:
	"""Base class for sockets."""

	__metaclass__ = ABCMeta

	def __init__(self, host):
		"""Create a socket, with the given host."""
		self.host = host

	def _log(self, event_type, fmt, *args, **kwargs):
		"""Logs a message, including details about this TcpSocket."""
		level = kwargs.get('level', logging.INFO)
		logging.getLogger(__name__).log(level, '%s %s %s '+fmt, self.local[0], self.local[1], event_type, *args, **kwargs)

	def sched_send(self, packet):
		self.host.send(packet)

	@abstractmethod
	def _buffer(self, packet):
		"""Called by the Host to pass a packet to this Socket."""
		pass

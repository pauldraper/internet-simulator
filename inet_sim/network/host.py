import logging

from .link import Link
from ..network.tcp import TcpSocket, TcpPacket
from ..network.udp import UdpSocket, UdpPacket

AF_INET = 'AF_INET' #IP
SOCK_DGRAM = 'SOCK_DGRAM'   #UDP
SOCK_STREAM = 'SOCK_STREAM' #TCP

class Host:
	"""Represents an endpoint on the Internet.
	Currently, a Host may have exactly one IP address.
	"""

	def __init__(self, ip):
		"""Construct a host with the given ip address."""
		self.ip = ip
		self.routing = {}        #ip address to link
		Link(self, self, 1e-6, 1e9) #loopback
		self.port_to_udp = {}
		self.port_to_tcp = {}
		self.origin_to_tcp = {}

	def __log(self, fmt, *args, **kwargs):
		level = kwargs.get('level', logging.INFO)
		logging.getLogger(__name__).log(level, 'host %s '+fmt, self.ip, *args)

	def sched_send(self, packet):
		"""Send packet."""
		try:
			link = self.routing[packet.dest]
		except KeyError:
			self.__log('no entry for %s', packet.dest, level=logging.WARNING)
		else:
			self.__log('send-packet %s', packet.dest)
			link.enqueue(packet)

	def received(self, packet):
		"""Called (by Link) to deliver a packet to this Host."""
		if packet.dest[0] != self.ip:
			self.__log('received packet for %s', packet.dest, level=logging.WARNING)
		elif isinstance(packet, UdpPacket):
			self.__log('recv-packet UDP %s', packet.origin)
			try:
				self.port_to_udp[packet.dest[1]]._buffer(packet)
			except KeyError:
				pass
		elif isinstance(packet, TcpPacket):
			self.__log('recv-packet TCP %s', packet.origin)
			try:
				self.origin_to_tcp[packet.origin]._buffer(packet)
			except KeyError:
				self.port_to_tcp[packet.dest[1]]._buffer(packet)
		else:
			raise Exception("Unrecognized protocol")

	# socket

	def socket(self, domain, sock_type):
		"""Create and return a socket of the appropriate type."""
		if domain == AF_INET and sock_type == SOCK_DGRAM:
			return UdpSocket(self)
		elif domain == AF_INET and sock_type == SOCK_STREAM:
			return TcpSocket(self)

	def get_available_udp(self):
		"""Return an available UDP port on this Host."""
		try:
			port = next(p for p in range(32768,65536) if p not in self.port_to_udp)
		except StopIteration:
			raise Exception('No available ports')
		return (self.ip, port)
		
	def get_available_tcp(self):
		"""Return an available TCP port on this Host."""
		try:
			port = next(p for p in range(32768,65536) if p not in self.port_to_tcp)
		except StopIteration:
			raise Exception('No available ports')
		return (self.ip, port)

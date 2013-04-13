from link import Link
from sim import logger
from tcp import TcpSocket
from udp import UDPSocket

log = lambda x: logger.log(x, 2)

AF_INET = 'AF_INET' #IP
SOCK_DGRAM = 'SOCK_DGRAM'   #UDP
SOCK_STREAM = 'SOCK_STREAM' #TCP

class Host:
	"""Represent a host on the Internet.
	A host may have exactly one IP address.
	"""

	ip_to_host = {} #maps from ip address to host

	def __init__(self, ip):
		"""Constuct a host with the given ip address."""
		if ip in Host.ip_to_host:
			raise Exception('duplicate ip address')
		self.ip = ip
		self.port_to_udp = {}
		self.port_to_tcp = {}
		self.origin_to_tcp = {}
		self.links = []
		Host.ip_to_host[ip] = self
		Link(self, self, 0, 100000)

	def __del__(self):
		"""Release this host's IP address for reuse."""
		del Host.ip_to_host[self.ip]

	# network

	def get_host(self, ip):
		"""Return the Host with the given IP address.
		This is called on a Host to allow for the possibility of have local IP addresses, but this
		functionality is not currently in use.
		"""
		return Host.ip_to_host[ip]

	def get_links(self, ip):
		"""Return the links that are connected to this Host."""
		host = self.getHost(ip)
		return (l for l in self.links if l.dest == host)

	# data transfer

	def received(self, packet):
		"""Called (by Link) to deliver a packet to this Host."""
		if packet.dest[0] != self.ip:
			raise Exception('this host does not have this ip %s' % (packet.dest[0],))
		elif packet.protocol == 'UDP':
			try:
				self.port_to_upd[packet.dest[1]]._buffer(packet)
			except KeyError:
				pass
		elif packet.protocol == 'Tcp':
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
			return UDPSocket(self)
		elif domain == AF_INET and sock_type == SOCK_STREAM:
			return TcpSocket(self)

	def getAvailableUDP(self):
		"""Return an available UDP port on this Host."""
		try:
			port = (p for p in xrange(32768,65536) if p not in self.port_to_udp).next()
		except StopIteration:
			raise Exception('No available ports')
		return (self.ip, port)
		
	def getAvailableTcp(self):
		"""Return an available TCP port on this Host."""
		try:
			port = (p for p in xrange(32768,65536) if p not in self.port_to_tcp).next()
		except StopIteration:
			raise Exception('No available ports')
		return (self.ip, port)

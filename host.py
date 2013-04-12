from link import Link
from sim import scheduler, logger
from tcp import TcpSocket
from udp import UDPSocket

log = lambda x: logger.log(x, 2)

AF_INET = 'AF_INET'
SOCK_DGRAM = 'SOCK_DGRAM'
SOCK_STREAM = 'SOCK_STREAM'

class Host:

	ip_to_host = {}
	id_counter = 0

	def __init__(self, ip):
		if ip in Host.ip_to_host:
			raise Exception('duplicate ip address')
		self.ip = ip
		self.port_to_udp = {}
		self.port_to_tcp = {}
		self.origin_to_tcp = {}
		self.links = []
		self.id = Host.id_counter
		Host.ip_to_host[ip] = self
		Host.id_counter += 1
		Link(self, self, 0, 100000)

	def __del__(self):
		del Host.ip_to_host[self.ip]

	# network
	def getHost(self, ip):
		return Host.ip_to_host[ip]

	def getLinks(self, ip):
		host = self.getHost(ip)
		return (l for l in self.links if l.dest == host)

	# data transfer
	def received(self, packet):
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
	def socket(self, domain, type):
		if domain == AF_INET and type == SOCK_DGRAM:
			return UDPSocket(self)
		elif domain == AF_INET and type == SOCK_STREAM:
			return TcpSocket(self)

	def getAvailableUDP(self):
		try:
			port = (p for p in xrange(32768,65536) if p not in self.port_to_udp).next()
		except StopIteration:
			raise Exception('No available ports')
		return (self.ip, port)
		
	def getAvailableTcp(self):
		try:
			port = (p for p in xrange(32768,65536) if p not in self.port_to_tcp).next()
		except StopIteration:
			raise Exception('No available ports')
		return (self.ip, port)

"""This has fallen into disuse and its functionality needs to be verfied."""
from collections import deque

from .link import Packet
from .socket import Socket
from ..log import logger

log = lambda x: logger.log(x, 2)

class UDPPacket(Packet):

	def __init__(self, origin, dest, message):
		Packet.__init__(self, message)
		self.origin = origin
		self.dest = dest
		self.local = self.host.getAvailableUDP()

	@property
	def size(self):
		return Packet.size(self) + 4

class UdpSocket(Socket):

	def __init__(self, host):
		Socket.__init__(self, host)
		self.packets = deque()

	def bind(self, addr):
		self.local = addr

	def connect(self, addr):
		self.remote = addr

	def sendto(self, message, addr):
		p = UDPPacket(self.local, addr, message)
		log('socket-send %s:%s %s:%s' % (p.origin[0], p.origin[1], p.dest[0], p.dest[1]))
		self.host.getLinks(addr[1]).next().enqueue(p)

	def send(self, message):
		if not hasattr(self, 'remote'):
			raise Exception("Must call connect() first")
		self.sendto(message, self.remote)

	def recvfrom(self, handler):
		self.recvfrom_handler = handler
		self.__check_buffer()

	def recv(self, handler):
		self.recv_handler = handler
		self.__check_buffer()

	def close(self):
		del self.local

	def _buffer(self, packet):
		if hasattr(self, 'remote') and packet.origin != self.remote:
			return
		self.packets.appendleft(packet)
		self.__check_buffer()

	def __try_handle(self):
		if self.packets: #if no packets buffered
			p = self.packets.pop()
			log('socket-recv %s:%s %s:%s' % (p.origin[0], p.origin[1], p.dest[0], p.dest[1]))
			if hasattr(self, 'recvfrom_handler'):
				scheduler.add(self.recvfrom_handler, [p.message, p.origin], 0)
				del self.recvfrom_handler
			elif hasattr(self, 'recv_handler'):
				scheduler.add(self.recv_handler, [p.message], 0)
				del self.recv_handler
				
	@property
	def local(self):
		return self.__local
	@local.setter
	def local(self, value):
		if self.host.ip != value[0]:
			raise Exception('%s is an invalid ip for this socket''s host' % (ip,))
		if self.host.port_to_socket.has_key(value[1]):
			raise Exception('Port %d is already bound on this host' % (value[1],))
		#remove
		if hasattr(self, 'local'):
			del self.local
		#add
		if value:
			self.host.port_to_socket[value[1]] = self
			self.__local = value
	@local.deleter
	def local(self):
		del self.host.port_to_handler[self._local[1]]
		del self.__local

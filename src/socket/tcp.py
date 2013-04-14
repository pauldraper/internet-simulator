from collections import Counter

from link import Packet
from sim import *
from .socket import Socket

log = lambda x: logger.log(x, 2)

class TcpPacket(Packet):
	"""Represents a TCP packet."""

	mss = 1500 #maximum segment size

	def __init__(self, origin, dest, message=None, seq_num=None, ack_num=None, syn=False, fin=False):
		"""Create a TCP packet."""
		Packet.__init__(self, 'TCP', origin, dest, message)
		self.seq_num = seq_num
		self.ack_num = ack_num
		self.ack = ack_num is not None
		self.syn = syn
		self.fin = fin

	@property
	def size(self):
		"""Return the size of this TcpPacket, in bytes."""
		return Packet.size.fget(self) + 8
		
	def __str__(self):
		"""Return a string representation of this TcpPacket."""
		flags = []
		if self.syn:
			flags.append('syn')
		if self.ack:
			flags.append('ack')
		if self.fin:
			flags.append('fin')
		s = '-'.join(flags if flags else ['data'])
		if self.ack_num is not None:
			s = '{} {}'.format(s, self.ack_num)
		if self.seq_num is not None:
			if self.message:
				s = '{} {}-{}'.format(s, self.seq_num, self.seq_num+len(self.message)-1)
			else:
				s = '{} {}'.format(s, self.seq_num)
		return s


class TcpSocket(Socket):
	"""Represents a TcpSocket."""

	def __init__(self, host):
		"""Create a TcpSocket."""
		Socket.__init__(self, host)
		self.inc = []           #incoming buffer
		self.inc_i = 0          #length of in-order bytes
		self.inc_read_i = 0     #length of read bytes
		self.out = []           #outgoing buffer
		self.out_i = 0          #length of bytes sent
		self.out_ack_i = 0      #length of bytes acknowledged
		self.cwnd = 15000       #window size
		self.ssthresh = 96000   #slow start threshold
		self.state = 'CLOSED'   #TCP state
		self.ack_counts = Counter()
		self.rtt = 8.           #estimated round trip time
		self.rtt_dict = {}      #expected ack --> time sent
		self.loss = self.tahoe_loss #TCP method for dealing with loss
		self.syn_event      = simulator.create_lock()
		self.syn_ack_event  = simulator.create_lock()
		self.ack_event      = simulator.create_lock()
		self.data_event     = simulator.create_lock()
		self.fin_event      = simulator.create_lock()
		self.loss_event     = simulator.create_lock()

	@property
	def timeout(self):
		return self.rtt * 1.5

	def log(self, s):
		"""Logs a message, including details about this TcpSocket."""
		local_str = '{addr[0]}:{addr[1]}'.format(addr=self.local)
		return log('{:15} {}'.format(local_str, s))

	# public methods

	def bind(self, addr):
		"""Bind the socket to the specified port."""
		self.local = addr
		self.host.port_to_tcp[addr[1]] = self
	
	def listen(self):
		"""Listen for connections to the bound port."""
		if not hasattr(self, 'local'):
			raise Exception('Must call bind() first')
		self.state = 'LISTEN'

	def accept(self):
		"""Accept a connection. The socket is returned."""
		if self.state != 'LISTEN':
			raise Exception('Must call listen() first')
		
		packet = (yield wait(self.syn_event))[0]
		socket = TcpSocket(self.host)
		socket.state = self.state
		socket.local = self.local
		socket.remote = packet.origin
		socket.host.origin_to_tcp[packet.origin] = socket
		
		socket.state = 'SYN_RCVD'
		socket.log('LISTEN <- SYN : SYN_RECVD -> SYN+ACK')
		socket.__sched_send(TcpPacket(socket.local, socket.remote, seq_num=0, ack_num=0, syn=True))
		
		return socket
		
	def connect(self, addr):
		"""Establish a connection to the specified address."""
		assert self.state == 'CLOSED'
		self.local = self.host.getAvailableTcp()
		self.host.port_to_tcp[self.local[1]] = self
		self.remote = addr
		
		self.state = 'SYN_SENT'
		self.log('CLOSED : SYN -> SYN_SENT')
		def syn():
			self.__sched_send(TcpPacket(self.local, self.remote, seq_num=0, syn=True))
			return wait(self.syn_ack_event, self.timeout)
		yield attempt(syn, 10)
		self.state = 'ESTABLISHED'
		self.log('SYN_SENT <- SYN_ACK : ESTABLISHED -> ACK')
		self.__sched_send(TcpPacket(self.local, self.remote, ack_num=0))

	def sendall(self, message):
		"""Send the message. Return only when finished."""
		if not hasattr(self, 'remote'):
			raise Exception('Must call connect() first')
		self.out += message
		while self.out_ack_i < len(self.out):	
			end = min(self.out_ack_i+self.cwnd, self.out_i+TcpPacket.mss, len(self.out))
			if self.out_i < end:
				message = self.out[self.out_i:end]
				self.__sched_send(TcpPacket(self.local, self.remote, message, seq_num=self.out_i))
				if end not in self.rtt_dict:
					self.rtt_dict[end] = simulator.scheduler.get_time()
				simulator.new_thread(self.loss(self.out_i, end))
				self.out_i = end
			else:
				yield wait(self.ack_event)
		yield resume(self.ack_event)
	
	def recv(self):
		"""Return incoming data. At least one byte will be returned, unless the other side has
		closed."""
		if not self.inc_read_i < self.inc_i:
			yield wait(self.data_event)
		message, self.inc_read_i = self.inc[self.inc_read_i:self.inc_i], self.inc_i 
		return message
	
	def close(self):
		"""Close this end of a connection."""
		def fin():
			self.__sched_send(TcpPacket(self.local, self.remote, seq_num=len(self.out), fin=True))
			return wait(self.ack_event, self.timeout)
		
		if self.state == 'ESTABLISHED' or self.state == 'SYN_RCVD':
			self.state = 'FIN_WAIT_1'
			self.log('ESTABLISHED : FIN -> FIN_WAIT_1')
			while self.out_ack_i < len(self.out):
				yield wait(self.ack_event)
			yield attempt(fin, 10)
			if self.state == 'FIN_WAIT_1':
				self.state = 'FIN_WAIT_2'
				self.log('FIN_WAIT_1 <- ACK : FIN_WAIT_2')
				yield wait(self.fin_event)
				self.state = 'TIME_WAIT'
				self.log('FIN_WAIT_2 <- FIN : ACK -> TIME_WAIT')
			elif self.state == 'CLOSING':
				self.state = 'TIME_WAIT'
				self.log('CLOSING <- ACK : TIME_WAIT')
			yield sleep(3*self.timeout)
			self.log('TIME_WAIT : CLOSED')
		
		elif self.state == 'CLOSE_WAIT':
			self.state = 'LAST_ACK'
			self.log('CLOSE_WAIT : FIN -> LAST_ACK')
			yield attempt(fin, 10)
			self.log('LAST_ACK <- ACK : CLOSED')

	# I/O

	def __sched_send(self, packet):
		"""Queue the packet on the appropriate link.
		This function is identical to Socket.scheduler_send, except for its debugging.
		"""
		self.log('-> %s' % (packet,))
		Socket.sched_send(self, packet)

	def _buffer(self, packet):
		"""Called by the Host to pass a packet to this Socket."""
		self.log('<- %s' % (packet,))   
		if packet.ack and packet.syn:
			yield self.__syn_ack(packet)
		elif packet.ack:
			yield self.__ack(packet)
		elif packet.syn:
			yield self.__syn(packet)
		elif packet.fin:
			yield self.__fin(packet)	
		else:
			yield self.__data(packet)
		
	# state changes

	def __syn_ack(self, packet):
		"""Handle a SYN+ACK packet."""
		yield resume(self.syn_ack_event)

	def __ack(self, packet):
		"""Handle an ACK packet."""
		if self.state == 'SYN_RCVD':
			self.state = 'ESTABLISHED'
			self.log('SYN_RCVD <- ACK : ESTABLISHED')
		if packet.ack_num <= len(self.out):
			#re-estimate rtt
			sent_time = self.rtt_dict.get(packet.ack_num, None)
			if sent_time:
				self.rtt = (self.rtt + simulator.scheduler.get_time() - sent_time) / 2
				self.rtt_dict[packet.ack_num] = None
				self.log('setting timeout to {socket.timeout:3f}'.format(socket=self))
			#check for triple ACKs
			self.ack_counts[packet.ack_num] += 1
			if self.ack_counts[packet.ack_num] >= 3: #triple ACKs
				yield resume(self.loss_event)
				return
			#adjust window
			elif packet.ack_num > self.out_ack_i:
				new_bytes = packet.ack_num - self.out_ack_i
				self.cwnd += (
					new_bytes if self.cwnd < self.ssthresh
					else int(new_bytes * TcpPacket.mss / self.cwnd)
				)
				self.out_ack_i = packet.ack_num
		yield resume(self.ack_event)

	def __syn(self, packet):
		yield resume(self.syn_event, packet)

	def __data(self, packet):
		"""Handle a data packet."""
		self.inc += (None,) * (packet.seq_num - len(self.inc))
		self.inc[packet.seq_num:packet.seq_num+len(packet.message)] = packet.message
		self.inc_i = next(
			(i for i,b in enumerate(self.inc[self.inc_i:], start=self.inc_i) if b is None),
			len(self.inc)
		)
		self.__sched_send(TcpPacket(self.local, self.remote, ack_num=self.inc_i))
		yield resume(self.data_event)

	def __fin(self, packet):
		"""Handle a FIN packet."""
		if self.state == 'SYN_RCVD':
			self.state = 'CLOSE_WAIT'
			self.log('SYN_RCVD <- FIN : ACK -> CLOSE_WAIT')
		elif self.state == 'ESTABLISHED':
			self.state = 'CLOSE_WAIT'
			self.log('ESTABLISHED <- FIN : ACK -> CLOSE_WAIT') 
		self.__sched_send(TcpPacket(self.local, self.remote, ack_num=packet.seq_num+1))
		yield resume(self.fin_event)

	#loss
	
	def tahoe_loss(self, start, end):
		"""Check for loss and compensate according to TCP Tahoe."""
		try:
			yield wait(self.loss_event, self.timeout)
		except TimeoutException:
			pass
		if start <= self.out_ack_i < end:
			log('loss_event')
			self.ack_counts.clear()
			self.out_i = self.out_ack_i
			self.ssthresh = int(max(self.cwnd/2, TcpPacket.mss))
			self.cwnd = TcpPacket.mss
			yield resume(self.ack_event)
			
	def reno_loss(self, start, end):
		"""Check for loss and compensate according to TCP Reno."""
		try:
			yield wait(self.loss_event, self.timeout)
			self.cwnd = max(self.cwnd // 2, TcpPacket.mss)
		except TimeoutException:
			self.cwnd = TcpPacket.mss
		if start <= self.out_ack_i < end:
			log('loss_event')
			self.ack_counts.clear()
			self.out_i = self.out_ack_i
			self.ssthresh = int(max(self.cwnd/2, TcpPacket.mss))
			yield resume(self.ack_event)
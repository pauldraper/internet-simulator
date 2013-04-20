from __future__ import division
import logging

from .link import Packet
from .socket import Socket
from sim import sim, Event, TimeoutException

class TcpPacket(Packet):
	"""Represents a TCP packet."""

	mss = 1500 #maximum segment size

	def __init__(self, origin, dest, message=None, seq_num=None, ack_num=None, syn=False, fin=False,
			timestamp=None):
		"""Create a TCP packet."""
		Packet.__init__(self, origin, dest, message)
		self.seq_num = seq_num
		self.ack_num = ack_num
		self.ack = ack_num is not None
		self.syn = syn
		self.fin = fin
		self.timestamp = timestamp if timestamp is not None else sim.time()

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


class Congestion:
	def __init__(self, socket):
		self.socket = socket
		self.cwnd = TcpPacket.mss
		self.ssthresh = 0
		self.dup_ack_count = 0
		self.min_ack = 0
		
	def ack(self, ack_num):
		#new ack
		if self.socket.out_ack_i < ack_num:
			num_bytes, self.socket.out_ack_i = ack_num - self.socket.out_ack_i, ack_num
			self.dup_ack_count = 0
			self.new_ack(num_bytes) #abstract method
			
		#dup ack
		elif self.socket.out_ack_i == ack_num:
			self.dup_ack(ack_num) #abstract method
	def timeout(self):
		self.dup_ack_count = 0
		self.after_timeout() #abstract method

class Reno(Congestion):
	SLOW_START = 0
	CONGESTION_AVOIDANCE = 1
	FAST_RECOVERY = 2
	
	def __init__(self, socket):
		Congestion.__init__(self, socket)
		self.state = Tahoe.SLOW_START
	def new_ack(self, num_bytes):
		num_bytes = TcpPacket.mss
		if self.state == Reno.SLOW_START:
			self.cwnd += num_bytes
			self.socket._log('cwnd-adjust', '{}'.format(self.cwnd))
			if self.cwnd >= self.ssthresh:
				self.state = Reno.CONGESTION_AVOIDANCE
		elif self.state == Reno.CONGESTION_AVOIDANCE:
			self.cwnd += int(num_bytes * TcpPacket.mss / self.cwnd)
			self.socket._log('cwnd-adjust', '{}'.format(self.cwnd))
		elif self.state == Reno.FAST_RECOVERY:
			self.cwnd = self.ssthresh
			self.socket._log('cwnd-adjust', '{}'.format(self.cwnd))
			self.state = Reno.CONGESTION_AVOIDANCE
	def dup_ack(self, ack_num):
		if self.state == Reno.FAST_RECOVERY:
			self.cwnd += TcpPacket.mss
			self.socket._log('cwnd-adjust', '{}'.format(self.cwnd))
		else:
			self.dup_ack_count += 1
			if self.dup_ack_count == 3:
				self.socket._send_data(ack_num)
				self.socket._log('loss', 'triple-ack {}'.format(ack_num))
				self.ssthresh = int(self.cwnd / 2)
				self.socket._log('ssthresh-adjust', '{}'.format(self.ssthresh))
				self.cwnd = self.ssthresh + 3 * TcpPacket.mss
				self.socket._log('cwnd-adjust', '{}'.format(self.cwnd))
				self.state = Reno.FAST_RECOVERY
	def after_timeout(self):
		self.ssthresh = int(self.cwnd / 2)
		self.socket._log('ssthresh-adjust', '{}'.format(self.ssthresh))
		self.cwnd = TcpPacket.mss
		self.socket._log('cwnd-adjust', '{}'.format(self.cwnd))
		self.state = Reno.SLOW_START
			
class Tahoe(Congestion):
	SLOW_START = 0
	CONGESTION_AVOIDANCE = 1
	
	def __init__(self, socket):
		Congestion.__init__(self, socket)
		self.state = Tahoe.SLOW_START
	def new_ack(self, num_bytes):
		if self.state == Tahoe.SLOW_START:
			self.cwnd += num_bytes
			self.socket._log('cwnd-adjust', '{}'.format(self.cwnd))
			if self.cwnd >= self.ssthresh:
				self.state = Tahoe.CONGESTION_AVOIDANCE
		elif self.state == Tahoe.CONGESTION_AVOIDANCE:
			self.cwnd += int(num_bytes * TcpPacket.mss / self.cwnd)
			self.socket._log('cwnd-adjust', '{}'.format(self.cwnd))
	def dup_ack(self, ack_num):
		pass
	def after_timeout(self):
		self.ssthresh = int(self.cwnd / 2)
		self.socket._log('ssthresh-adjust', '{}'.format(self.ssthresh))
		self.cwnd = TcpPacket.mss
		self.socket._log('cwnd-adjust', '{}'.format(self.cwnd))
		self.state = Tahoe.SLOW_START

class TcpSocket(Socket):
	"""Represents a TcpSocket."""		

	def __init__(self, host):
		"""Create a TcpSocket."""
		Socket.__init__(self, host)
		self.inc = []		  #incoming buffer
		self.inc_i = 0		  #length of in-order bytes
		self.inc_read_i = 0	  #length of read bytes
		self.out = []		  #outgoing buffer
		self.out_i = 0		  #length of bytes sent
		self.out_ack_i = 0	  #length of bytes acknowledged
		self.state = 'CLOSED'  #TCP state
		self._timeout = 3.
		self._cwnd = TcpPacket.mss
		self._ssthresh = 96000
		self.last_loss = 0
		self.ack_count = 0    #count of last acks
		self.congestion  = Tahoe(self) #TCP method for dealing with loss
		self.syn_event	   = Event()
		self.syn_ack_event = Event()
		self.ack_event	   = Event()
		self.data_event	   = Event()
		self.fin_event	   = Event()

	"""Timeout."""
	@property
	def timeout(self):
		return self._timeout
	@timeout.setter
	def timeout(self, value):
		self._timeout = value
		self._log('timeout-adjust', '{socket.timeout}'.format(socket=self))

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
		
		packet = self.syn_event.wait()
		socket = TcpSocket(self.host)
		socket.state = self.state
		socket.local = self.local
		socket.remote = packet.origin
		socket.host.origin_to_tcp[packet.origin] = socket
		
		socket.state = 'SYN_RCVD'
		socket._log('state', 'LISTEN <- SYN : SYN_RCVD -> SYN+ACK')
		socket.__sched_send(TcpPacket(socket.local, socket.remote, seq_num=0, ack_num=0, syn=True,
			timestamp=packet.timestamp))
		
		return socket
		
	def connect(self, addr):
		"""Establish a connection to the specified address."""
		assert self.state == 'CLOSED'
		self.local = self.host.get_available_tcp()
		self.host.port_to_tcp[self.local[1]] = self
		self.remote = addr
		
		self.state = 'SYN_SENT'
		self._log('state', 'CLOSED : SYN -> SYN_SENT')
		def syn():
			self.__sched_send(TcpPacket(self.local, self.remote, seq_num=0, syn=True))
			return self.syn_ack_event.wait(self.timeout)
		packet = attempt(syn, 10)
		self.state = 'ESTABLISHED'
		self._log('state', 'SYN_SENT <- SYN_ACK : ESTABLISHED -> ACK')
		self.__sched_send(TcpPacket(self.local, self.remote, ack_num=0, timestamp=packet.timestamp))

	def _send_data(self, start):
		"""Send a single data packet beginning at start, if data is available.
		Return the next sequence number after this packet, or None is no data was available.
		"""
		end = min(self.out_ack_i+self.congestion.cwnd, start+TcpPacket.mss, len(self.out))
		if start < end:
			message = self.out[start:end]
			self.__sched_send(TcpPacket(self.local, self.remote, message, seq_num=start))
			return end

	def sendall(self, message):
		"""Send the message. Return only when finished."""
		if not hasattr(self, 'remote'):
			raise Exception('Must call connect() first')
		self.out += message
		while self.out_ack_i < len(self.out):
			end = self._send_data(self.out_i)
			if end is not None:
				def loss(start=self.out_i, end=end, timeout=self.timeout):
					time = sim.time()
					sim.sleep(self.timeout)
					if start <= self.out_ack_i < end and self.last_loss < time \
							and self.congestion.min_ack < end:
						self.congestion.min_ack = end
						self.out_i = start
						self.last_loss = time
						self.timeout *= 2
						self._log('loss', 'timeout {:.4}'.format(timeout))
						self.congestion.timeout()
						self.ack_event.notify()
				
				sim.new_thread(loss)
				self.out_i = end
			else:
				self.ack_event.wait()
	
	def recv(self):
		"""Return incoming data. At least one byte will be returned, unless the other side has
		closed."""
		while self.state in ('SYN_RCVD', 'ESTABLISHED', 'TIME_WAIT_1', 'TIME_WAIT_2') \
				and not self.inc_read_i < self.inc_i:
			self.data_event.wait()
		message, self.inc_read_i = self.inc[self.inc_read_i:self.inc_i], self.inc_i 
		return message
	
	def close(self):
		"""Close this end of a connection."""
		def fin():
			self.__sched_send(TcpPacket(self.local, self.remote, seq_num=len(self.out), fin=True))
			self.ack_event.wait(self.timeout)
		
		if self.state == 'ESTABLISHED' or self.state == 'SYN_RCVD':
			self.state = 'FIN_WAIT_1'
			self._log('state', 'ESTABLISHED : FIN -> FIN_WAIT_1')
			while self.out_ack_i < len(self.out):
				self.ack_event.wait()
			attempt(fin, 10)
			if self.state == 'FIN_WAIT_1':
				self.state = 'FIN_WAIT_2'
				self._log('state', 'FIN_WAIT_1 <- ACK : FIN_WAIT_2')
				self.fin_event.wait()
				self.state = 'TIME_WAIT'
				self._log('state', 'FIN_WAIT_2 <- FIN : ACK -> TIME_WAIT')
			elif self.state == 'CLOSING':
				self.state = 'TIME_WAIT'
				self._log('state', 'CLOSING <- ACK : TIME_WAIT')
			sim.sleep(3*self.timeout)
			self._log('state', 'TIME_WAIT : CLOSED')
		
		elif self.state == 'CLOSE_WAIT':
			self.state = 'LAST_ACK'
			self._log('state', 'CLOSE_WAIT : FIN -> LAST_ACK')
			attempt(fin, 10)
			self._log('state', 'LAST_ACK <- ACK : CLOSED')

	# I/O

	def __sched_send(self, packet):
		"""Queue the packet on the appropriate link.
		This function is identical to Socket.scheduler_send, except for its debugging.
		"""
		self._log('send', '-> %s' % (packet,))
		Socket.sched_send(self, packet)

	def _buffer(self, packet):
		"""Called by the Host to pass a packet to this Socket."""
		self._log('recv', '<- %s' % (packet,))   
		if packet.ack and packet.syn:
			self.__syn_ack(packet)
		elif packet.ack:
			self.__ack(packet)
		elif packet.syn:
			self.__syn(packet)
		elif packet.fin:
			self.__fin(packet)	
		else:
			self.__data(packet)
		
	# state changes

	def __syn_ack(self, packet):
		"""Handle a SYN+ACK packet."""
		self.syn_ack_event.notify(packet)

	def __ack(self, packet):
		"""Handle an ACK packet."""
		self.timeout = (self.timeout + 2.5 * (sim.time() - packet.timestamp)) / 2
		if self.state == 'SYN_RCVD':
			self.state = 'ESTABLISHED'
			self._log('state', 'SYN_RCVD <- ACK : ESTABLISHED')
		if packet.ack_num <= len(self.out):
			self.congestion.ack(packet.ack_num)
		self.ack_event.notify()

	def __syn(self, packet):
		if self.state == 'SYN_RCVD' or self.state == 'ESTABLISHED':
			self.__sched_send(TcpPacket(packet.dest, self.remote, seq_num=0, ack_num=0, syn=True))
		self.syn_event.notify(packet)

	def __data(self, packet):
		"""Handle a data packet."""
		self.inc += (None,) * (packet.seq_num - len(self.inc))
		self.inc[packet.seq_num:packet.seq_num+len(packet.message)] = packet.message
		self.inc_i = next(
			(i for i,b in enumerate(self.inc[self.inc_i:], start=self.inc_i) if b is None),
			len(self.inc)
		)
		self.__sched_send(TcpPacket(self.local, self.remote, ack_num=self.inc_i
			, timestamp=packet.timestamp))
		self.data_event.notify()

	def __fin(self, packet):
		"""Handle a FIN packet."""
		if self.state == 'SYN_RCVD':
			self.state = 'CLOSE_WAIT'
			self._log('state', 'SYN_RCVD <- FIN : ACK -> CLOSE_WAIT')
		elif self.state == 'ESTABLISHED':
			self.state = 'CLOSE_WAIT'
			self._log('state', 'ESTABLISHED <- FIN : ACK -> CLOSE_WAIT') 
		self.__sched_send(TcpPacket(self.local, self.remote, ack_num=packet.seq_num+1
			, timestamp=packet.timestamp))
		self.data_event.notify()
		self.fin_event.notify()

def attempt(f, n):
	for _ in xrange(1, n):
		try:
			return f()
		except TimeoutException:
			pass
	return f()

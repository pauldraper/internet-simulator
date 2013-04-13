from link import Packet
from sim import scheduler, logger
from socket import Socket

log = lambda x: logger.log(x, 2)

class TcpPacket(Packet):
	"""Represents a TCP packet."""

	max_len = 1500

	def __init__(self, origin, dest, message=None, seq_num=None, ack_num=None, syn=False, fin=False):
		"""Create a TCP packet."""
		Packet.__init__(self, 'Tcp', origin, dest, message)
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
		s = ''
		
		flags = []
		if self.syn:
			flags.append('syn')
		if self.ack:
			flags.append('ack')
		if self.fin:
			flags.append('fin')
		s += '-'.join(flags if flags else ['data'])
		
		if self.ack_num is not None:
			s += ' %d' % (self.ack_num,)
		if self.seq_num is not None:
			if self.message:
				s += ' %d-%d' % (self.seq_num, self.seq_num+len(self.message)-1)
			else:
				s += ' %d' % (self.seq_num,)

		return s


class TcpSocket(Socket):
	"""Represents a TcpSocket."""

	def __init__(self, host, rtt=5.):
		"""Create a TcpSocket."""
		Socket.__init__(self, host)
		self.inc = [] #incoming buffer
		self.inc_i = 0         #length of in-order bytes
		self.out = [] #outgoing buffer
		self.out_i = 0         #length of sent bytes
		self.out_window = 15000 #window size
		self.state = 'CLOSED'  #Tcp state
		self.rtt = rtt
		self.rtt_dict = {}
		self.timeout = rtt * 1.5 #timeout (for all events)

	def log(self, s):
		"""Logs a message, including details about this TcpSocket."""
		local_str = '%s:%d' % (self.local[0], self.local[1])
		return log('%15s %s' %  (local_str, s))

	# public methods

	def bind(self, (ip, port)):
		"""Bind the socket to the specified port. (Called by server.)"""
		self.local = (ip, port)
		self.host.port_to_tcp[port] = self
	
	def listen(self):
		"""Listens for connections to the bound port. (Called by server.)"""
		if not hasattr(self, 'local'):
			raise Exception('Must call bind() first')
		self.state = 'LISTEN'

	def accept(self, callback):
		"""Call the callback when a connection has been established. (Called by server.)
		The callback will be passed the newly create TcpSocket.
		"""
		if self.state != 'LISTEN':
			raise Exception('Must call listen() first')
		self.callback = callback

	def connect(self, (ip, port), callback):
		"""Call the callback when a connection to the specified address has been established.
		(Called by client.) The	callback is passed a boolean, indicating whether the connection was
		sucessful.
		"""
		self.local = self.host.getAvailableTcp()
		self.host.port_to_tcp[self.local[1]] = self
		self.remote = (ip, port)
		self.callback = callback
		self.__conn()

	def sendall(self, message, callback):
		"""Send the message, and then call the callback when the entire message has been
		acknowledged.
		"""
		if not hasattr(self, 'remote'):
			raise Exception('Must call connect() first')
		self.send_callback = callback
		self.__try_send(message)
	
	def recv(self, callback):
		"""Wait until at least one byte is received, and then call the callback. The callback is
		passed the message that was received."""
		self.recv_callback = callback
		if self.state == 'ESTABLISHED' or self.state == 'CLOSE_WAIT':
			self.__try_read()
		else:
			scheduler.add(callback, (None,))
	
	def close(self):
		"""Close the connection."""
		self.__end()

	# I/O

	def _buffer(self, packet):
		"""Called by the Host to pass a packet to this TcpSocket."""
		self.log('<- %s' % (packet,))    
		if packet.syn:
			if self.state == 'LISTEN':
				s = TcpSocket(self.host, self.timeout)
				s.state = self.state
				s.local = self.local
				s.remote = packet.origin
				self.host.origin_to_tcp[packet.origin] = s
				s.callback = self.callback
				s.__syn(packet)
			elif packet.ack:
				self.__syn_ack(packet)
		elif packet.ack:
			self.__ack(packet)			
		elif packet.fin:
			self.__fin(packet)	
		else:
			self.__data(packet)

	def sched_send(self, packet):
		"""Enque the packet on the appropriate link.
		This function is identical to Socket.scheduler_send, except for its debugging.
		"""
		self.log('-> %s' % (packet,))
		Socket.schedule_send(self, packet)
		
	def sched_closed(self):
		"""Schedule a transition to the closed state."""
		scheduler.add(self.__closed, delay=4*self.timeout)

	def __try_read(self, ack=False):
		"""Attempt to read."""
		#find last in-order received
		recv_len = next(
			(i for i,b in enumerate(self.inc[self.inc_i:], start=self.inc_i) if b is None),
			len(self.inc)
		)
		#acknowledge
		if ack:
			self.sched_send(TcpPacket(self.local, self.remote, ack_num=recv_len))
		#callback
		bytes = self.inc[self.inc_i:recv_len]
		if bytes and hasattr(self, 'recv_callback'):
			self.inc_i = recv_len
			scheduler.add(self.recv_callback, (''.join(bytes),))
			del self.recv_callback
			
	def __try_send(self, data=''):
		"""Attempt to send."""
		#start of data to send
		start = min(self.out_i+self.out_window, len(self.out))
		#copy data to buffer
		self.out += data
		self.out_i = next(
			(i for i,b in enumerate(self.out[self.out_i:], start=self.out_i) if b is not None),
			len(self.out)
		)
		#end of data to send
		end = min(self.out_i+self.out_window, len(self.out))
		#send data
		for p_start in xrange(start, end, TcpPacket.max_len):
			p_end = min(end,p_start+TcpPacket.max_len)
			p = TcpPacket(self.local, self.remote, ''.join(self.out[p_start:p_end]), seq_num=p_start)
			def s(p=p):
				self.rtt_dict[p_end] = scheduler.get_time()
				self.sched_send(p)
			self.__do_while(
				s,
				lambda p_end=p_end: self.out_i < p_end
			)

	# state changes

	def __conn(self):
		"""Initiate connection start."""
		if self.state == 'CLOSED':
			self.state = 'SYN_SENT'
			def set_failed(self=self):
				self.failed = True
				scheduler.add(self.callback)
			self.__do_while(
				lambda: self.sched_send(TcpPacket(self.local, self.remote, seq_num=0, syn=True)),
				lambda: self.state == 'SYN_SENT',
				set_failed,
			)	
			self.log('CLOSED : SYN -> SYN_SENT')

	def __syn(self, packet):
		"""Handle a SYN packet."""
		if self.state == 'LISTEN':
			self.remote = packet.origin
			self.state = 'SYN_RCVD'
			self.log('LISTEN <- SYN : SYN_RECVD -> SYN+ACK')
			self.__do_while(
				lambda: self.sched_send(TcpPacket(self.local, self.remote, seq_num=0, ack_num=0, syn=True)),
				lambda: self.state == 'SYN_RCVD'
			)

	def __ack(self, packet):
		"""Handle an ACK packet."""
		if self.state == 'SYN_RCVD':
			scheduler.add(self.callback, (self,packet.origin))
			del self.callback
			self.state = 'ESTABLISHED'
			self.log('SYN_RCVD <- ACK : ESTABLISHED')
		if packet.ack_num <= len(self.out):
			diff = packet.ack_num - self.out_i
			self.out[self.out_i:packet.ack_num] = (None,) * diff
			self.__try_send()
			if packet.ack_num in self.rtt_dict:
				self.rtt = (self.rtt + scheduler.get_time() - self.rtt_dict[packet.ack_num]) / 2.
				del self.rtt_dict[packet.ack_num]
				self.timeout = self.rtt * 1.5
				#print self.rtt
		elif self.state == 'FIN_WAIT_1':
			self.state = 'FIN_WAIT_2'
			self.log('FIN_WAIT_1 <- ACK : FIN_WAIT_2')
		elif self.state == 'CLOSING':
			self.state = 'TIME_WAIT'
			self.log('CLOSING <- ACK : TIME_WAIT')
			self.sched_closed()
		elif self.state == 'LAST_ACK':
			self.state = 'CLOSED'
			self.log('CLOSED <- ACK : CLOSED')

		if hasattr(self, 'send_callback') and self.out_i == len(self.out):
			scheduler.add(self.send_callback)
			del self.send_callback

	def __syn_ack(self, packet):
		"""Handle a SYN+ACK packet."""
		if self.state == 'SYN_SENT':
			self.sched_send(TcpPacket(self.local, self.remote, ack_num=0))
			scheduler.add(self.callback)
			del self.callback
			self.state = 'ESTABLISHED'
			self.log('SYN_SENT <- SYN_ACK : ESTABLISHED -> ACK')

	def __data(self, packet):
		"""Handle a data packet."""
		if self.state == 'SYN_RCVD':
			scheduler.add(self.callback, (self,packet.origin))
			del self.callback
			self.state = 'ESTABLISHED'
			self.log('SYN_RCVD <- data : ESTABLISHED')
		self.inc += (None,) * (packet.seq_num - len(self.inc))
		self.inc[packet.seq_num:packet.seq_num+len(packet.message)] = packet.message
		self.__try_read(ack=True)

	def __fin(self, packet):
		"""Handle a FIN packet."""
		if hasattr(self, 'recv_callback'):
			scheduler.add(self.recv_callback, (None,))
			del self.recv_callback
		if self.state == 'ESTABLISHED':
			self.state = 'CLOSE_WAIT'
			self.log('ESTABLISHED <- FIN : ACK -> CLOSE_WAIT') 
		elif self.state == 'FIN_WAIT_1':
			self.state = 'CLOSING'
			self.log('FIN_WAIT_1 <- FIN : ACK -> CLOSING') 
		elif self.state == 'FIN_WAIT_2':
			self.state = 'TIME_WAIT'
			self.log('FIN_WAIT2 <- FIN : ACK -> TIME_WAIT') 
			self.sched_closed()
		self.sched_send(TcpPacket(self.local, self.remote, ack_num=packet.seq_num+1))

	def __end(self):
		"""Close this end of a connection."""
		if self.state == 'ESTABLISHED' or self.state == 'SYN_RCVD':
			self.state = 'FIN_WAIT_1'
			self.log('ESTABLISHED : FIN -> FIN_WAIT_1')
			self.__do_while(
				lambda: self.sched_send(TcpPacket(self.local, self.remote, seq_num=len(self.out), fin=True)),
				lambda: self.state == 'FIN_WAIT_1' or self.state == 'CLOSING'
			)
		elif self.state == 'CLOSE_WAIT':
			self.state = 'LAST_ACK'
			self.log('CLOSE_WAIT : FIN -> LAST_ACK')
			self.__do_while(
				lambda: self.sched_send(TcpPacket(self.local, self.remote, seq_num=len(self.out), fin=True)),
				lambda: self.state == 'LAST_ACK'
			)

	def __closed(self):
		"""Set state to CLOSED."""
		self.state = 'CLOSED'
		self.log('TIME_WAIT : CLOSED')

	# utility

	def __do_while(self, f, pred=lambda:True, failure=lambda:None, n=20):
		"""Execute function at intervals specified by self.timeout until the predicate is false."""
		if n <= 0:
			failure()
		elif pred():
			f()
			scheduler.add(self.__do_while, (f,pred,failure,n-1), self.timeout)

		


from __future__ import division
from datetime import datetime
import logging
import random

from inet_sim.network.host import AF_INET, Host, SOCK_STREAM
from inet_sim.network.link import Link
from sim import sim

def generate(self, function, args, avg_delay, duration):
	"""Generate events with exponential distribution."""
	frequency = 1 / avg_delay
	end_time = duration + sim.time()
	sim.sleep(random.expovariate(frequency))
	while end_time <= sim.time():
		sim.sleep(random.expovariate(frequency))
		function(*args)

class Server:

	def __init__(self, host, port):
		self.socket = host.socket(AF_INET, SOCK_STREAM)
		self.socket.bind((host.ip, port))
	
	def run(self):
		self.socket.listen()
		self.handle_conn(self.socket.accept())
		
	def end(self):
		self.socket.close()

	def handle_conn(self, socket):
		message = ''
		while not message or message[-1] != '\n':
			message += ''.join(socket.recv())
		logging.getLogger(__name__).info(message[:-1])
		if message[:4] == 'time':
			socket.sendall('%s' % (datetime.now(),), self.socket.close)
		elif message[:4] == 'file':
			socket.sendall(open(message[5:-1], 'rb').read())
		else:
			socket.sendall('unrecognized request')
		socket.close()
			
class TimeClient:

	def __init__(self, host, addr):
		self.socket = host.socket(AF_INET, SOCK_STREAM)
		self.addr = addr

	def get_time(self):
		self.socket.connect(self.addr)
		self.socket.sendall('time\n')
		message = ''
		while True:
			m = self.socket.recv()
			if not m:
				break
			message += m
		logging.getLogger(__name__).info(message)
		self.socket.close()

class FileClient:

	def __init__(self, host, addr):
		self.socket = host.socket(AF_INET, SOCK_STREAM)
		self.addr = addr

	def download_file(self):
		self.socket.connect(self.addr)
		self.socket.sendall('file large.jpg\n')
		file = open('downloaded.jpg', 'wb')
		while True:
			m = self.socket.recv()
			if not m:
				break
			file.write(''.join(m))
		file.close()
		self.socket.close()

def demo_client_server(host1, host2, n_client=1, n_server=1):
	sim.__init__()
	server_ip = host2.ip
	for i in range(0,n_client):
		def c(client=FileClient(host1, (server_ip, 80+i))):
			#sleep(i*15)
			client.download_file()
		sim.new_thread(c)	
	for i in range(0,n_server):
		server = Server(host2, 80+i)
		sim.new_thread(server.run)
		#def stop(server=server):
		#	sim.sleep(5)
		#	server.end()
		#sim.new_thread(stop)
	sim.run()

def configure_logging(level):
	import sys
	logging.basicConfig(stream=sys.stdout, level=level)
	class Formatter(logging.Formatter):
		def format(self, record):
			if record.levelno == logging.DEBUG:
				self._fmt = '%(name)s - %(message)s'
			else:
				record.time = sim.time()
				self._fmt = '%(time)7.4f %(message)s'
			return super(Formatter, self).format(record)
	logging.getLogger().handlers[0].setFormatter(Formatter())
	logging.getLogger('inet_sim.network.link').setLevel(logging.FATAL)

if __name__ == '__main__':
	configure_logging(logging.INFO)
	
	# intialize network
	host1 = Host('123.0.0.0')
	host2 = Host('101.0.0.0')
	link1 = Link(host1, host2, 0.5, 104000)
	link2 = Link(host2, host1, 0.5, 104000)
	link1.loss = .0
	link2.loss = .0
	
	demo_client_server(host1, host2, 1, 1)

	# clean up
	del host1
	del host2

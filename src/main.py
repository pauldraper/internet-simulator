from datetime import datetime
import random

from host import *
from link import Link
from sim import simulator, sleep

log = lambda x: logger.log(x, 1)

def generate(self, function, args, avg_delay, duration):
	"""Generate events with exponential distribution."""
	frequency = 1 / avg_delay
	end_time = duration + simulator.scheduler.get_time()
	yield sleep(random.expovariate(frequency))
	while end_time <= simulator.scheduler.get_time():
		yield sleep(random.expovariate(frequency))
		yield function(*args)

class Server:

	def __init__(self, host, port):
		self.socket = host.socket(AF_INET, SOCK_STREAM)
		self.socket.bind((host.ip, port))
	
	def run(self):
		self.socket.listen()
		yield self.handle_conn((yield self.socket.accept()))
		
	def end(self):
		yield self.socket.close()

	def handle_conn(self, socket):
		message = ''
		while not message or message[-1] != '\n':
			message += ''.join((yield socket.recv()))
		log(message[:-1])
		if message[:4] == 'time':
			yield socket.sendall('%s' % (datetime.now(),), self.socket.close)
		elif message[:4] == 'file':
			yield socket.sendall(open(message[5:-1], 'rb').read())
		else:
			yield socket.sendall('unrecognized request')
		yield socket.close()
			
class TimeClient:

	def __init__(self, host, addr):
		self.socket = host.socket(AF_INET, SOCK_STREAM)
		self.addr = addr

	def get_time(self):
		yield self.socket.connect(self.addr)
		yield self.socket.sendall('time\n')
		message = ''
		while True:
			m = yield self.socket.recv()
			if not m:
				break
			message += m
		log(message)
		yield self.socket.close()

class FileClient:

	def __init__(self, host, addr):
		self.socket = host.socket(AF_INET, SOCK_STREAM)
		self.addr = addr

	def download_file(self):
		yield self.socket.connect(self.addr)
		yield self.socket.sendall('file xkcd1058.png\n')
		file = open('downloaded_%d.png' % (random.randint(1,10000000),), 'wb')
		while True:
			m = yield self.socket.recv()
			if not m:
				break
			file.write(bytes(m))
		file.close()
		yield self.socket.close()

def demo_client_server(host1, host2, n_client=1, n_server=1):
	simulator.__init__()
	server_ip = host2.ip
	for _ in range(0,n_client):
		client = FileClient(host1, (server_ip, 80+random.randrange(n_server)))
		simulator.new_thread(client.download_file())	
	for i in range(0,n_server):
		server = Server(host2, 80+i)
		simulator.new_thread(server.run())
		def stop(server=server):
			yield sleep(5)
			yield server.end()
		simulator.new_thread(stop())
	simulator.run()

if __name__ == '__main__':
	# intialize network
	host1 = Host('123.0.0.0')
	host2 = Host('101.0.0.0')
	link1 = Link(host1, host2, 0.5, 10000)
	link2 = Link(host2, host1, 0.5, 10000)
	link1.loss = .1
	link2.loss = .1

	logger.level = 2
	
	demo_client_server(host1, host2, 1, 1)

	# clean up
	del host1
	del host2

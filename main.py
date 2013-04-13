from datetime import datetime

from link import *
from host import *

log = lambda x: logger.log(x, 1)

class Server:

	def __init__(self, host, port):
		self.socket = host.socket(AF_INET, SOCK_STREAM)
		self.socket.bind((host.ip, port))
		self.socket.listen()
		self.socket.accept(self.handle_connection)
		
	def end(self):
		self.socket.close()

	def handle_connection(self, socket, addr):
		self.socket.accept(self.handle_connection)
		socket.recv(Server.Conn(socket).handle_recv)
	
	class Conn:
		def __init__(self, socket):
			self.socket = socket
			self.buffer = ''
		
		def handle_recv(self, message):
			self.buffer += message
			if self.buffer[-1] != '\n':
				self.socket.recv(self.handle_recv)
			else:
				print self.buffer[:-1]
				if self.buffer[:4] == 'time':
					self.socket.sendall('%s' % (datetime.now(),), self.socket.close)
				elif self.buffer[:4] == 'file':
					self.socket.sendall(open(self.buffer[5:-1], 'rb').read(), self.socket.close)
				else:
					self.socket.sendall('unrecognized request', self.socket.close)
					
			
class TimeClient:

	def __init__(self, host, (ip, port)):
		self.socket = host.socket(AF_INET, SOCK_STREAM)
		self.socket.connect((ip, port), self.get_time)
		self.buffer = ''
		
	def get_time(self):
		if not hasattr(self.socket, 'failed'):
			self.socket.sendall('time\n', lambda: self.socket.recv(self.handle_recv))
		
	def handle_recv(self, message):
		if message:
			self.buffer += message
			self.socket.recv(self.handle_recv)
		else:
			print self.buffer
			self.socket.close()
			

class FileClient:

	def __init__(self, host, (ip, port)):
		self.socket = host.socket(AF_INET, SOCK_STREAM)
		self.socket.connect((ip, port), self.download_file)
		self.file = open('downloaded_%d.png' % (random.randint(1,10000000),), 'w')
		
	def download_file(self):
		if not hasattr(self.socket, 'failed'):
			self.socket.sendall('file xkcd1058.png\n', lambda: self.socket.recv(self.handle_recv))
		
	def handle_recv(self, message):
		if message:
			self.file.write(message)
			self.socket.recv(self.handle_recv)
		else:
			self.file.close()
			self.socket.close()


def demo_client_server(host1, host2, n_client=1, n_server=1):
	scheduler.__init__()
	server_ip = host2.ip
	# intialize sockets
	clients = [
		FileClient(host1, (server_ip, 80+random.randrange(n_server)))
		for _ in xrange(0,n_client)
	]
	servers = [
		Server(host2, 80+i)
		for i in xrange(0,n_server)
	]

	scheduler.run()

	map(Server.end, servers)

if __name__ == '__main__':
	# intialize network
	host1 = Host('123.0.0.0')
	host2 = Host('101.0.0.0')
	link1 = Link(host1, host2, 0.5, 100)
	link2 = Link(host2, host1, 0.5, 100)
	link1.loss = .0
	link2.loss = .0

	logger.level = 2
	
	demo_client_server(host1, host2, 1, 1)

	# clean up
	del host1
	del host2

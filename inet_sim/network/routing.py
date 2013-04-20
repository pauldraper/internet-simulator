from __future__ import division
import operator
import pickle
import logging

from sim import sim
from link import IpPacket

class RoutingPacket(IpPacket):
	
	PING = 0
	VECTOR = 1
	
	def __init__(self, origin, dest, message):
		IpPacket.__init__(self, origin, dest, message)

class Routing:
	def recv(self, packet, link):
		type, value = pickle.loads(packet.message)
		if type == RoutingPacket.PING:
			self.__incoming_to_outgoing[link].enqueue(RoutingPacket) 
		self.__matrix[packet.ip][link] = (sim.time() - value) / 2
		vector = {ip : max(d.iteritems(), key=operator.itemgetter(1))[0] for ip, d in self.__matrix}
		
	def __getitem__(self, ip):
		return min(self.__matrix[ip].iteritems(), key=operator.itemgetter(1))[0]
	
from .routing import Routing

class Node:
	"""Represents an node on the Internet."""

	def __init__(self, ip):
		"""Construct a host with the given ip address."""
		self.ip = ip
		self.__incoming_to_outgoing = {}
		self.__vector = None # ip to distance
		self.__matrix = None # ip to link to distance

	def __log(self, fmt, *args, **kwargs):
		level = kwargs.get('level', logging.INFO)
		logging.getLogger(__name__).log(level, 'node %s '+fmt, self.ip, *args)

	def add_link(self, outgoing, incoming):
		self.__incoming_to_outgoing[incoming] = outgoing

	def send(self, packet):
		"""Send packet."""
		try:
			link = next(v for v in self.__incoming_to_outgoing.values() if v.dest.ip == packet.dest)
		except KeyError:
			self.__log('no entry for %s', packet.dest, level=logging.WARNING)
		else:
			self.__log('send-packet %s', packet.dest)
			link.enqueue(packet)

	def received(self, packet, link):
		"""Called (by Link) to deliver a packet to this Node."""
		self.__log('recv-packet %s', packet.dest)
		if packet.dest != self.ip:
			pass
		elif isinstance(packet, RoutingPacket):
			self.__log('recv-packet ROUTING %s', packet.origin[0])
			self.__routing.recv(packet, link)
		else:
			self.handle(packet)

	def handle(self, packet):
		raise Exception("Unrecognized protocal")

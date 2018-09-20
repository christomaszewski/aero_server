import json
import socket
import struct

class JsonSocket(object):
	def __init__(self, sock=None, udp=False):
		if sock is None:
			if udp == False:
				self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			else:
				self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		else:
			self._socket = sock

		#self._conn = self._socket

		# Must be 2 right now because struct.pack/unpack are hardcoded below
		self._header_size = 2

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		if isinstance(value, RuntimeError):
			print("Socket connection broken, closing socket...")
			self.close()
			return True

	def _send(self, msg):
		sent = 0
		print ('msg length is ', len(msg))
		while sent < len(msg):
			print (msg[sent:])
			sent += self._socket.send(msg[sent:])

	def _read(self, size):
		data = bytearray()
		while len(data) < size:
			new_data = self._socket.recv(size - len(data))
			#print(new_data)
			data.extend(new_data)
			if new_data == b'':
				#print("Socket connection broken, handle appropriately")
				raise RuntimeError("Socket connection broken")

		return data

	def _msg_length(self):
		header = self._read(self._header_size)
		length = struct.unpack('!H', header)[0]
		#int.from_bytes(header, byteorder='big')

		return length


	def send_obj(self, obj, encoder=json.JSONEncoder):
		msg = json.dumps(obj, cls=encoder, indent=2)

		if self._socket:
			print(len(msg), len(msg.encode('utf-8')))
			# Python 3
			#format_str = f"={len(msg)}s"
			format_str = "!H{0}s".format(len(msg))
			# msg_packed = struct.pack(format_str, msg.encode('utf-8'))
			msg_length = len(msg)
			msg_packed = struct.pack(format_str,msg_length,msg)
			#msg_length.to_bytes(self._header_size, byteorder='big')

			print("Sending packed message {0}".format(msg_packed))
			self._send(msg_packed)
			# print("Sending packed message bytes {0}".format(msg_packed))
			# print("bytes are ", list(bytearray(msg_packed)))
			# self._send(msg_packed)

	def read_obj(self, decoder=json.JSONDecoder):
		size = self._msg_length()
		data = self._read(size)
		# Python 3
		#format_str = f"={size}s"
		format_str = "={0}s".format(size)
		msg = struct.unpack(format_str, data)[0]

		return json.loads(msg, cls=decoder)

	def close(self):
		self._socket.close()

	@property
	def socket(self):
		return self._socket

	@socket.setter
	def socket(self, new_socket):
		self._socket = new_socket


class JsonServer(JsonSocket):

	def __init__(self, address=None, port=None):
		# Python 3
		#super().__init__()
		super(JsonServer, self).__init__()

		self._address = address
		self._port = port


	def bind(self, address, port):
		if address is None:
			address = socket.gethostname()

		print("binding to {0}".format(address))
		self.socket.bind((address, port))
		self._address = address
		self._port = port

	def listen(self):
		self.socket.listen(0)

	def accept(self):
		conn, addr = self._socket.accept()
		#conn.settimeout(2.0)

		return JsonSocket(conn)


class JsonClient(JsonSocket):

	def __init__(self, address=None, port=None, use_udp=False):
		# Python 3
		#super().__init__()
		super(JsonClient, self).__init__(udp=use_udp)

		self._address = address
		self._port = port

	def connect(self, address, port):
		self.socket.connect((address, port))

		self._address = address
		self._port = port

class MulticastJsonClient(JsonSocket):

	def __init__(self, address=None, port=None):
		super(MulticastJsonClient, self).__init__(udp=True)

		ttl = struct.pack('b', 1)
		self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

	def connect(self, address, port):
		self._address = address
		self._port = port

	def _send_to(self, msg, address, port):
		sent = 0
		while sent < len(msg):
			sent += self._socket.sendto(msg[sent:], (address, port))

	def send_obj(self, obj, encoder=json.JSONEncoder):
		msg = json.dumps(obj, cls=encoder, indent=2)

		format_str = "!H{0}s".format(len(msg))
		msg_length = len(msg)
		msg_packed = struct.pack(format_str,msg_length,msg)

		print("Sending packed message {0}".format(msg_packed))
		self._send_to(msg_packed, self._address, self._port)
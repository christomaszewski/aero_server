import threading
import Queue
import time
from messages import Message
import logging


class CommandParser(threading.Thread):

	def __init__(self, socket, cmd_queue, control_thread):
		self._socket = socket
		self._cmd_queue = cmd_queue
		self._control_thread = control_thread
		self._is_alive = False

		self._logger = logging.getLogger('command_server_log')

		super(CommandParser, self).__init__()

	def start(self):
		self._is_alive = True

		super(CommandParser, self).start()

	def stop(self):
		self._is_alive = False

	def run(self):
		with self._socket:
			while self._is_alive:
				try:
					message = self._socket.read_obj(decoder=Message.json_decoder)
					payload = message.payload

					#Todo maybe parse commands here?
					if message.type == 'CMD':
						self._cmd_queue.put(message)
						self._logger.info("Got Command {0}. Pushed to command queue".format(message))

					elif message.type == 'CTRL':
						if payload['cmd'] == 'SAFETY_STOP':
							self._control_thread.safety_behavior()
						if payload['cmd'] == 'INTERRUPT':
							self._control_thread.interrupt()
						elif payload['cmd'] == 'RESUME':
							self._control_thread.resume()
						elif payload['cmd'] == 'HEARTBEAT':
							self._control_thread.update_heartbeat(time.time())
					elif message.type == 'CONFIG':
						if payload['cmd'] == 'SET':
							pass
							
					else:
						self._logger.warning("Got unrecognized message {0}".format(message))

				except:
					self._logger.error("An exception occured while trying to parse message {0}".format(message))

class MessageDispatcher(threading.Thread):

	def __init__(self, socket, msg_queue):
		self._socket = socket
		self._msg_queue = msg_queue
		self._is_alive = False

		self._logger = logging.getLogger('command_server_log')

		super(MessageDispatcher, self).__init__()

	def start(self):
		self._is_alive = True

		super(MessageDispatcher, self).start()

	def stop(self):
		self._is_alive = False

	def run(self):
		with self._socket:
			while self._is_alive:
				# Read message from response queue and write it out to the socket
				try:
					msg = self._msg_queue.get(timeout=3)
				except Queue.Empty as e:
					#handle empty command queue, add autonomy here
					self._logger.info("Message Queue is empty")
					msg = None

				if msg is not None:
					self._socket.send_obj(msg, encoder=Message.json_encoder)


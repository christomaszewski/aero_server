import threading
import Queue
import time
from messages import Message
import logging
import sys
import socket


class CommandParser(threading.Thread):

	def __init__(self, socket, cmd_queue, control_thread, server_config):
		self._socket = socket
		self._cmd_queue = cmd_queue
		self._control_thread = control_thread
		self._server_config = server_config
		self._is_alive = False

		self._logger = logging.getLogger('command_server_log')

		super(CommandParser, self).__init__()

	def start(self):
		self._is_alive = True

		super(CommandParser, self).start()

	def stop(self):
		if self._is_alive:
			self._socket.close()

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
						self._logger.info("Got CTRL Command {0}. Processing.".format(message))
						if payload['cmd'] == 'SAFETY_STOP':
							self._control_thread.safety_behavior()
						if payload['cmd'] == 'INTERRUPT':
							self._control_thread.interrupt()
						elif payload['cmd'] == 'RESUME':
							self._control_thread.resume()
						elif payload['cmd'] == 'HEARTBEAT':
							self._control_thread.update_heartbeat(time.time())
					elif message.type == 'CONFIG':
						self._logger.info("Got CONFIG Command {0}. Processing.".format(message))
						if payload['cmd'] == 'SET' and 'param' in payload and 'value' in payload:
							self._server_config[payload['param']] = payload['value']
							
							if payload['param'] == 'failsafe_mission':
								self._server_config.failsafe_confirmed = True

							param_dict = {payload['param']:self._server_config[payload['param']]}
							response_msg = Message.from_info_dict(param_dict)
							self._socket.send_obj(response_msg, Message.json_encoder)
							
						elif payload['cmd'] == 'GET' and 'param' in payload:
							param_dict = {payload['param']:self._server_config[payload['param']]}
							response_msg = Message.from_info_dict(param_dict)
							self._socket.send_obj(response_msg, Message.json_encoder)

						else:
							self._logger.warning("Got unknown CONFIG message {0}".format(message))
							
					else:
						self._logger.warning("Got unrecognized message {0}".format(message))

				except socket.error:
					self._logger.warning("Socket was closed while attempting to read, closing socket and shutting down thread.")
					self.stop()

				except Exception as e:
					name = sys.exc_info()[0]
					trace = sys.exc_info()[2]
					self._logger.error("A {0} exception occured while trying to parse message {1}".format(name, message))
					self._logger.debug("Traceback: {0}".format(trace))
				except:
					self._logger.error("An unknown exception occured while trying to parse message {0}".format(message))

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
			while self._is_alive and not self._socket.marked_as_closed:
				# Read message from response queue and write it out to the socket
				try:
					msg = self._msg_queue.get(timeout=3)
				except Queue.Empty as e:
					#handle empty command queue, add autonomy here
					self._logger.info("Message Queue is empty")
					msg = None

				try:
					if msg is not None:
						self._socket.send_obj(msg, encoder=Message.json_encoder)
				except socket.error:
						self._logger.warning("Socket was closed while attempting to write to it, pushing message back onto queue.")
						self._msg_queue.put(msg)
						self._stop()


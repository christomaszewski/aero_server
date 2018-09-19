from jsocket import JsonServer
import Queue
from control import DroneController
from command import CommandParser, MessageDispatcher
from messages import Message
import json
import sys
import signal
import time

# Initialize Settings (Todo: Read in from file)
server_settings = {'rally_point':None}

# Create command and response queues
cmd_queue = Queue.Queue()
response_queue = Queue.Queue()

# Spawn control thread and pass queue reference
control_thread = DroneController(cmd_queue)
control_thread.start()

# Setup json server to receive commands and push them to cmd queue
jserver = JsonServer()
jserver.bind('', 6760)
jserver.listen()

# Initialize list of threads for clean shutdown purposes
thread_pool = [control_thread]


# Add signal handler to kill all threads
def clean_shutdown(sig, frame):
	print("Server shutting down...")
	for t in thread_pool:
		t.stop()
	
	jserver.close()

	for t in thread_pool:
		t.join()

	sys.exit(0)

signal.signal(signal.SIGINT, clean_shutdown)


while True:
	jsock = jserver.accept()

	cmd_thread = CommandParser(jsock, cmd_queue, control_thread)
	cmd_thread.start()

	response_thread = MessageDispatcher(jsock, response_queue)
	response_thread.start()

	thread_pool.append(cmd_thread)
	thread_pool.append(response_thread)

	"""
	# Todo spawn separate thread to handle parsing the message and pushing it to the queue
	with jsock:
		while True:
			message = jsock.read_obj(decoder=Message.json_decoder)

			#Todo maybe parse commands here?
			if message.type == 'CMD':
				cmd_queue.put(message)
				print("Got Command {0}. Pushed to command queue".format(message))

			elif message.type == 'CTRL':
				if payload['cmd'] == 'INTERRUPT':
					control_thread.interrupt()
				elif payload['cmd'] == 'RESUME':
					control_thread.resume()
				elif payload['cmd'] == 'HEARTBEAT':
					control_thread.update_heartbeat(time.time())
			elif message.type == 'CONFIG':
				if payload['cmd'] == 'SET':
					pass


					
			else:
				print("Got unrecognized message {0}".format(message))
	"""

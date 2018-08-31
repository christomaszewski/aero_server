from jsocket import JsonServer
import Queue
from control import DroneController
from messages import Message
import json
import sys
import signal


# Create command queue 
cmd_queue = Queue.Queue()

# Spawn control thread and pass queue reference
control_thread = DroneController(cmd_queue)
control_thread.start()

# Setup json server to receive commands and push them to cmd queue
jserver = JsonServer()
jserver.bind('', 6760)
jserver.listen()


# Add signal handler to kill all threads
def clean_shutdown(sig, frame):
	print("Server shutting down...")
	control_thread.stop()
	jserver.close()
	control_thread.join()
	sys.exit(0)

signal.signal(signal.SIGINT, clean_shutdown)


while True:
	jsock = jserver.accept()

	# Todo spawn separate thread to handle parsing the message and pushing it to the queue
	with jsock:
		while True:
			message = jsock.read_obj(decoder=Message.json_decoder)

			#Todo maybe parse commands here?
			if message.type == 'CMD':
				cmd_queue.put(message)
				print("Got Command {0}. Pushed to command queue".format(message))
			else:
				print("Got unrecognized message {0}".format(message))

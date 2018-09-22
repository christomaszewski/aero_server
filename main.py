from jsocket import JsonServer
import Queue
from control import DroneController
from command import CommandParser, MessageDispatcher
from messages import Message
import json
import sys
import signal
import time
import logging

# Initialize and Setup Logger
logger = logging.getLogger(name='command_server_log')
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s - %(funcName)s - Line: %(lineno)d - %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)

# Create command and response queues
cmd_queue = Queue.Queue()
response_queue = Queue.Queue()

# Spawn control thread and pass queue reference
control_thread = DroneController(cmd_queue, response_queue)
control_thread.start()

# Setup json server to receive commands and push them to cmd queue
jserver = JsonServer()
jserver.bind('', 6760)
jserver.listen()

# Initialize list of threads for clean shutdown purposes
thread_pool = [control_thread]


# Add signal handler to kill all threads
def clean_shutdown(sig, frame):
	logger.info("Server shutting down")
	for t in thread_pool:
		t.stop()
	
	jserver.close()

	for t in thread_pool:
		t.join()

	logging.shutdown()
	sys.exit(0)

signal.signal(signal.SIGINT, clean_shutdown)


while True:
	jsock = jserver.accept()

	# Add log message with ip from connected client

	cmd_thread = CommandParser(jsock, cmd_queue, control_thread)
	cmd_thread.start()

	response_thread = MessageDispatcher(jsock, response_queue)
	response_thread.start()

	thread_pool.append(cmd_thread)
	thread_pool.append(response_thread)

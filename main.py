from jsocket import JsonServer
import Queue
from control import DroneController
from command import CommandParser, MessageDispatcher
from messages import Message
from config import Config
import json
import sys
import signal
import time
import logging
import os

# Define aero_server src dir
src_dir = "/home/aero/src/aero_server"

# Initialize and Setup Logger
logger = logging.getLogger(name='command_server_log')
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s - %(funcName)s - Line: %(lineno)d - %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)

# Setup logfile and add file handler to logger
log_dir = "{0}/logs".format(src_dir)
if not os.path.exists(log_dir):
	os.makedirs(log_dir)

log_filename = "{0}/{1}.txt".format(log_dir, time.strftime('%d_%m_%Y_%H_%M_%S'))
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Attempt to load server config file
server_config_filename = "{0}/server.conf".format(src_dir)
server_config = None
with open(server_config_filename, 'r') as f:
	server_config = json.load(f, cls=Config.json_decoder)

# Create command and response queues
cmd_queue = Queue.Queue()
response_queue = Queue.Queue()

# Spawn control thread and pass queue reference
control_thread = DroneController(cmd_queue, response_queue, server_config)
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

	cmd_thread = CommandParser(jsock, cmd_queue, control_thread, server_config)
	cmd_thread.start()

	response_thread = MessageDispatcher(jsock, response_queue)
	response_thread.start()

	thread_pool.append(cmd_thread)
	thread_pool.append(response_thread)
	thread_pool = [t for t in thread_pool if t.is_alive()]

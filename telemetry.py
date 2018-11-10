#!/usr/bin/python
from messages import Message, MessageEncoder
from jsocket import JsonClient, MulticastJsonClient
from collections import defaultdict
import itertools
import pymavlink.mavutil as mavutil
import threading
import yaml
import Queue
import json
import ast
import sys
import time

# Define aero_server src dir
src_dir = "/home/aero/src/aero_server"

# Initialize and Setup Logger
logger = logging.getLogger(name='telemetry_server_log')
logger.setLevel(logging.DEBUG)

# Setup logfile and add file handler to logger
log_dir = "{0}/logs".format(src_dir)
if not os.path.exists(log_dir):
	os.makedirs(log_dir)

log_filename = "{0}/telemetry_log_{1}.txt".format(log_dir, time.strftime('%d_%m_%Y_%H_%M_%S'))
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

class TelemetrySender(object):

	server_ip = None

	def __init__(self, ipaddr):
		self.server_ip = ipaddr
		self._logger = logging.getLogger('telemetry_server_log')

	def init_message_dispatch(self):
		message_queue = Queue.Queue()
		msgd_t = threading.Thread(target=self.message_dispatch,args=(message_queue,))
		msgd_t.start()

		msgg_t = threading.Thread(target=self.get_messages,args=(message_queue,))
		msgg_t.setDaemon(True) #if network thread dies this should too
		msgg_t.start()


	def message_dispatch(self,message_queue):
		ready = False
		while not ready:
			print('attempting to connect to ', self.server_ip)
			jsock = MulticastJsonClient()
			try:
				jsock.connect(self.server_ip, 10010)
				ready = True
			except:
				self._logger.warn("Socket Refused")
				time.sleep(5)



		print('connected to ', self.server_ip)
		current_time = lambda: str(int(round(time.time() * 1000)))
		while True:
			if message_queue.empty():
				pass

			msg = str(message_queue.get())

			tag = msg.partition(' ')[0]
			payload = msg.split(' ', 1)[1]

			try:

				json_payload =  yaml.load(payload) #converts to dict
				json_payload['time'] = current_time() #add timestamp

				net_msg = Message(tag,json_payload)

				jsock.send_obj(net_msg, encoder=Message.json_encoder)
			except:
				#print('connection down')
				pass

	def get_messages(self,message_queue):
		mav = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
		mav.wait_heartbeat()

                types_of_interest = set([ 'GLOBAL_POSITION_INT',
                                      'ATTITUDE',
                                      'BATTERY_STATUS',
                                      'STATUSEXT',
                                      'MISSION_ITEM_REACHED',
                                      'MISSION_CURRENT'
                                      'EXTENDED_SYS_STATE' ])

                msg_count = {t:0 for t in types_of_interest}
                msg_send_rate = defaultdict(itertools.repeat(1).next, { 'GLOBAL_POSITION_INT' : 20,
                                                                        'ATTITUDE'            : 20,
                                                                        'BATTERY_STATUS'      : 20,
                                                                        'STATUSEXT'           : 1,
                                                                        'MISSION_ITEM_REACHED': 1,
                                                                        'MISSION_CURRENT'     : 1,
                                                                        'EXTENDED_SYS_STATE'  : 5  })
		while True:
			msg = mav.recv_match(blocking=True)
			msg_type = msg.get_type()
			if msg_type not in msg_count:
				msg_count[msg_type] = 0

			if msg is not None and msg_count[msg_type] % msg_send_rate[msg_type] == 0:
				if msg_type in types_of_interest:
					message_queue.put(msg)
					self._logger.info(msg)
				else:
					self._logger.debug(msg)

			msg_count[msg_type] += 1

			"""
			msg = mav.recv_match(type=types_of_interest, blocking=True)
			msg_type = msg.get_type()
			if msg is not None and msg_count[msg_type] % msg_send_rate[msg_type] == 0:
				message_queue.put(msg)

			msg_count[msg_type] += 1
			"""




#init_message_dispatch()
t = TelemetrySender('224.0.0.150')
t.init_message_dispatch()

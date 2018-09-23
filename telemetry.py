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

class TelemetrySender(object):

	server_ip = None

	def __init__(self, ipaddr):
		self.server_ip = ipaddr



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
			jsock = JsonClient(use_udp=True)
			#jsock = MulticastJsonClient()
			try:
				jsock.connect(self.server_ip, 6781)
				ready = True
			except:
				print("Socket Refused")
				time.sleep(5)



		print('connected to ', self.server_ip)
		current_time = lambda: str(int(round(time.time() * 1000)))
		while True:
			if message_queue.empty():
				pass

			msg = str(message_queue.get())

			tag = msg.partition(' ')[0]
			payload = msg.split(' ', 1)[1]

			json_payload =  yaml.load(payload) #converts to dict
			json_payload['time'] = current_time() #add timestamp

			net_msg = Message(tag,json_payload)

			try:
				jsock.send_obj(net_msg, encoder=Message.json_encoder)
			except:
				#print('connection down')
				pass

	def get_messages(self,message_queue):
		mav = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
		mav.wait_heartbeat()

		types_of_interest = ['GLOBAL_POSITION_INT', 'MISSION_CURRENT', 'PARAM_VALUE', 'ATTITUDE', 'BATTERY_STATUS', 'COMMAND_LONG', 
									'EXTENDED_SYS_STATE', 'HOME_POSITION', 'MISSION_ITEM_REACHED', 'STATUSTEXT', 'SYS_STATUS']

		msg_count = {t:0 for t in types_of_interest}
		msg_send_rate = defaultdict(itertools.repeat(1).next, {'GLOBAL_POSITION_INT':20, 'ATTITUDE':20})

		while True:
			msg = mav.recv_match(type=types_of_interest, blocking=True)
			msg_type = msg.get_type()
			if msg is not None and msg_count[msg_type] % msg_send_rate[msg_type] == 0:
				message_queue.put(msg)

			msg_count[msg_type] += 1

#init_message_dispatch()
t = TelemetrySender('192.168.1.56')
#t = TelemetrySender('224.0.0.150')
t.init_message_dispatch()

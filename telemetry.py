from messages import Message, MessageEncoder
from jsocket import JsonClient
import pymavlink.mavutil as mavutil
import threading
import yaml
import Queue
import json
import ast

class TelemetrySender(object):

    server_ip = None

    def __init__(self,ipaddr):
        self.server_ip = ipaddr

    def init_message_dispatch(self):
        message_queue = Queue.Queue()
        msgd_t = threading.Thread(target=self.message_dispatch,args=(message_queue,))
        msgd_t.start()
        msgg_t = threading.Thread(target=self.get_messages,args=(message_queue,))
        msgg_t.start()

    def message_dispatch(self,message_queue):
        print 'attempting to connect to ', self.server_ip
        jsock = JsonClient(_udp=True)
        jsock.connect(self.server_ip, 6780)
        print 'connected to ', self.server_ip

        while True:
            if message_queue.empty():
                pass

            msg = str(message_queue.get())

            tag = msg.partition(' ')[0]
            payload = msg.split(' ', 1)[1]

            json_payload =  yaml.load(payload) #converts names into strings from raw values

            net_msg = Message(tag,json_payload)
            jsock.send_obj(net_msg, lambda obj: json.dumps(obj, cls=net_msg.json_encoder, indent=2))

    def get_messages(self,message_queue):
    #have to make sure msg is a string for this to work
        mav = mavutil.mavlink_connection('udp:127.0.0.1:5760')
        mav.wait_heartbeat()

        while True:
            msg = mav.recv_match(blocking=True)
            if msg is None:
                pass
            message_queue.put(msg)



#init_message_dispatch()
#t = TelemetrySender('192.168.0.132')
t = TelemetrySender('127.0.0.1')
t.init_message_dispatch()

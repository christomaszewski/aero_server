from jsocket import JsonClient
from messages import Message, MessageEncoder
import json
import time

msg_type = 'CMD'
arm_payload = {'cmd':'ARM'}
disarm_payload = {'cmd':'DISARM'}

arm_msg = Message(msg_type, arm_payload)
disarm_msg = Message(msg_type, disarm_payload)

jsock = JsonClient()
jsock.connect('192.168.1.201', 6780)

print("Connected, sending arm message {0}".format(arm_msg))
jsock.send_obj(arm_msg, lambda obj: json.dumps(obj, cls=arm_msg.json_encoder, indent=2))

time.sleep(15)

jsock.send_obj(disarm_msg, lambda obj: json.dumps(obj, cls=disarm_msg.json_encoder, indent=2))

time.sleep(3)

jsock.close()

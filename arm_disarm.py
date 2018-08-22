from jsocket import JsonClient
from messages import Message, MessageEncoder
import json
import time

msg_type = 'CMD'
arm_payload = {'cmd':'ARM_DISARM', 'value':'ARM'}
disarm_payload = {'cmd':'ARM_DISARM', 'value':'DISARM'}

arm_msg = Message(msg_type, arm_payload)
disarm_msg = Message(msg_type, disarm_payload)

jsock = JsonClient()
jsock.connect('192.168.0.114', 6780)

print("Connected, sending arm message {0}".format(arm_msg))
jsock.send_obj(disarm_msg, lambda obj: json.dumps(obj, cls=disarm_msg.json_encoder, indent=2))

#time.sleep(3)

jsock.send_obj(disarm_msg, lambda obj: json.dumps(obj, cls=disarm_msg.json_encoder, indent=2))

time.sleep(10)

jsock.close()
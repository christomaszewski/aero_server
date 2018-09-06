from jsocket import JsonClient
from messages import Message
import json
import time

msg_type = 'CMD'
arm_payload = {'cmd':'ARM'}
disarm_payload = {'cmd':'DISARM'}

arm_msg = Message(msg_type, arm_payload)
disarm_msg = Message(msg_type, disarm_payload)

jsock = JsonClient()
jsock.connect('172.16.0.123', 6760)

print("Connected, sending arm message {0}".format(arm_msg))
jsock.send_obj(arm_msg, encoder=arm_msg.json_encoder)

time.sleep(15)

jsock.send_obj(disarm_msg, encoder=disarm_msg.json_encoder)

time.sleep(3)

jsock.close()

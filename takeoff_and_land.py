from jsocket import JsonClient
from messages import Message
import json
import time

msg_type = 'CMD'
arm_payload = {'cmd':'ARM'}
disarm_payload = {'cmd':'DISARM'}
takeoff_payload = {'cmd':'TAKEOFF', 'target_altitude':2.5}
land_payload = {'cmd':'LAND'}


arm_msg = Message(msg_type, arm_payload)
disarm_msg = Message(msg_type, disarm_payload)
takeoff_msg = Message(msg_type, takeoff_payload)
land_msg = Message(msg_type, land_payload)

jsock = JsonClient()
jsock.connect('172.16.0.123', 6760)

print("Connected, sending arm message")
jsock.send_obj(arm_msg, encoder=arm_msg.json_encoder)

time.sleep(2)

print("Taking off...")
jsock.send_obj(takeoff_msg, encoder=takeoff_msg.json_encoder)

# Hover for 10 seconds
time.sleep(10)

print("Landing...")
jsock.send_obj(land_msg, encoder=land_msg.json_encoder)

time.sleep(3)

jsock.close()

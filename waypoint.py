from jsocket import JsonClient
from messages import Message, MessageEncoder
import json
import time

msg_type = 'CMD'
arm_payload = {'cmd':'ARM_DISARM', 'value':'ARM'}
disarm_payload = {'cmd':'ARM_DISARM', 'value':'DISARM'}
takeoff_payload = {'cmd':'TAKEOFF', 'target_altitude':2.5}
land_payload = {'cmd':'LAND'}
wp_payload = {'cmd':'WAYPOINT', 'LATITUDE':40.5993701, 'LONGITUDE':-80.0091235, 'ALTITUDE':3.0}


arm_msg = Message(msg_type, arm_payload)
disarm_msg = Message(msg_type, disarm_payload)
takeoff_msg = Message(msg_type, takeoff_payload)
land_msg = Message(msg_type, land_payload)
wp_msg = Message(msg_type, wp_payload)

jsock = JsonClient()
jsock.connect('192.168.1.221', 6780)

print("Connected, sending arm message")
jsock.send_obj(arm_msg, lambda obj: json.dumps(obj, cls=arm_msg.json_encoder, indent=2))

time.sleep(2)

print("Taking off...")
jsock.send_obj(takeoff_msg, lambda obj: json.dumps(obj, cls=takeoff_msg.json_encoder, indent=2))

# Hover for 10 seconds
time.sleep(10)

print("Moving to waypoint")
jsock.send_obj(wp_msg, lambda obj: json.dumps(obj, cls=wp_msg.json_encoder, indent=2))

time.sleep(20)

print("Landing...")
jsock.send_obj(land_msg, lambda obj: json.dumps(obj, cls=land_msg.json_encoder, indent=2))

# Make sure drone has landed before disarming
#time.sleep(10)

# Don't send disarm for now until landing is demonstrated
#jsock.send_obj(disarm_msg, lambda obj: json.dumps(obj, cls=disarm_msg.json_encoder, indent=2))

time.sleep(3)

jsock.close()

from messages import Message
import json

msg_type = 'CMD'
arm_payload = {'cmd':'ARM'}
disarm_payload = {'cmd':'DISARM'}
takeoff_payload = {'cmd':'TAKEOFF', 'target_altitude':2.5}
land_payload = {'cmd':'LAND'}
wp_payload = {'cmd':'WAYPOINT', 'LATITUDE':40.5993701, 'LONGITUDE':-80.0091235, 'ALTITUDE':3.0}

arm_msg = Message(msg_type, arm_payload)
disarm_msg = Message(msg_type, disarm_payload)
takeoff_msg = Message(msg_type, takeoff_payload)
land_msg = Message(msg_type, land_payload)
wp_msg = Message(msg_type, wp_payload)

mission = [arm_msg, takeoff_msg, wp_msg, land_msg]

with open('waypoint_mission.json', 'w') as f:
	for cmd in mission:
		json.dump(cmd, f, cls=cmd.json_encoder)
		f.write('\n')

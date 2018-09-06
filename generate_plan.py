from messages import Message
import json

msg_type = 'CMD'
arm_payload = {'cmd':'ARM'}
disarm_payload = {'cmd':'DISARM'}
takeoff_payload = {'cmd':'TAKEOFF', 'target_altitude':2.5}
land_payload = {'cmd':'LAND'}
wp_payload = {'cmd':'WAYPOINT', 'latitude':40.5993701, 'longitude':-80.0091235, 'altitude':3.0}
mission_payload = {'cmd':'MISSION', 'cmd_list':[{'cmd':'WAYPOINT', 'latitude':40.5993701, 'longitude':-80.0091235, 'altitude':3.0},
																{'cmd':'WAYPOINT', 'latitude':40.5993701, 'longitude':-80.0091235, 'altitude':3.0},
																{'cmd':'WAYPOINT', 'latitude':40.5993701, 'longitude':-80.0091235, 'altitude':3.0}]}


arm_msg = Message(msg_type, arm_payload)
disarm_msg = Message(msg_type, disarm_payload)
takeoff_msg = Message(msg_type, takeoff_payload)
land_msg = Message(msg_type, land_payload)
wp_msg = Message(msg_type, wp_payload)
mission_msg = Message(msg_type, mission_payload)

plan = [arm_msg, mission_msg, land_msg]

with open('waypoint_plan.json', 'w') as f:
	for cmd in plan:
		json.dump(cmd, f, cls=cmd.json_encoder)
		f.write('\n')

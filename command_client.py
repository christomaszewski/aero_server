from messages import Message
import json
import sys
import time

if len(sys.argv) != 4:
	print("Usage: python command_client.py server_ip server_port mission_file")
	sys.exit(0)

server_ip = sys.argv[1]
server_port = sys.argv[2]
mission_file = sys.argv[3]

jsock = JsonClient()
jsock.connect(server_ip, server_port)

with open(mission_file, 'r') as mission:
	for cmd in mission:
		cmd_msg = json.loads(cmd, cls=Message.json_decoder)
		jsock.send_obj(takeoff_msg, encoder=Message.json_encoder)
		time.sleep(5)
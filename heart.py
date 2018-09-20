from messages import Message
from jsocket import JsonClient
import json
import sys
import time

if len(sys.argv) != 3:
	print("Usage: python heart.py server_ip server_port")
	sys.exit(0)

server_ip = sys.argv[1]
server_port = int(sys.argv[2])

jsock = JsonClient()
jsock.connect(server_ip, server_port)

while True:
	cmd_msg = json.loads('{"cmd": "HEARTBEAT", "type": "CTRL"}', cls=Message.json_decoder)
	jsock.send_obj(cmd_msg, encoder=Message.json_encoder)
	time.sleep(1)
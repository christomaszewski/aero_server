from jsocket import JsonServer
from messages import Message, MessageEncoder
import json 

jserver = JsonServer()
jserver.bind('192.168.1.228', 6781)
jserver.listen()

jsock = jserver.accept()

print("Got connection")
while True:
	message = jsock.read_obj(lambda msg: json.loads(msg, object_hook=MessageEncoder.decode))
	print("{0}".format(message))
	#jsock.send_obj(message, lambda msg: json.dumps(msg, cls=message.json_encoder, indent=2))

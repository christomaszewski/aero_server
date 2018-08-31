from jsocket import JsonServer
from messages import Message
import json 

jserver = JsonServer()
jserver.bind('', 6760)
jserver.listen()

jsock = jserver.accept()

print("Got connection")
while True:
	message = jsock.read_obj(decoder=Message.json_decoder)
	print("{0}".format(message))
	#jsock.send_obj(message, lambda msg: json.dumps(msg, cls=message.json_encoder, indent=2))

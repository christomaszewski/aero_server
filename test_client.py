from jsocket import JsonClient
from messages import Message
import json


msg_type = 'TEST'
payload = {'data_1':666, 'data_2':'test_data'}

msg = Message(msg_type, payload)

jsock = JsonClient()
jsock.connect('192.168.0.142', 6781)

print("Connected, sending message {0}".format(msg))
jsock.send_obj(msg, encoder=msg.json_encoder)

#new_message = jsock.read_obj(lambda obj: json.loads(obj, object_hook=MessageEncoder.decode))

#print("Got message back {0}".format(new_message))


jsock.close()
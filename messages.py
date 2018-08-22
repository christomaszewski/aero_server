import json

class MessageEncoder(json.JSONEncoder):

	def default(self, data):
		# Python 3
		#return {'type':data.type, **data.payload}

		dict_rep = dict(data.payload)
		dict_rep['type'] = data.type

		return dict_rep

	@classmethod
	def decode(cls, json_dict):
		msg_type = json_dict['type']
		del json_dict['type']

		return Message(msg_type, json_dict)


class Message(object):

	json_encoder = MessageEncoder

	def __init__(self, msg_type, payload):
		self._type = msg_type
		self._payload = payload

	def __str__(self):
		return "{._type} {._payload}".format(self, self)

	@property
	def type(self):
		return self._type
	
	@property
	def payload(self):
		return self._payload
	
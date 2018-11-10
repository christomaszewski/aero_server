import json

class MessageEncoder(json.JSONEncoder):

	def default(self, obj):
		if isinstance(obj, Message):
			# Python 3
			#return {'type':obj.type, **obj.payload}

			dict_rep = dict(obj.payload)
			dict_rep['type'] = obj.type

			return dict_rep
		else:
			return super(MessageDecoder, self).default(obj)


class MessageDecoder(json.JSONDecoder):

	def __init__(self, *args, **kwargs):
		super(MessageDecoder, self).__init__(object_hook=self.object_hook, *args, **kwargs)

	def object_hook(self, obj):
		if 'type' not in obj:
			return obj

		msg_type = obj['type']
		del obj['type']

		return Message(msg_type, obj)


class Message(object):
	json_decoder = MessageDecoder
	json_encoder = MessageEncoder

	def __init__(self, msg_type, payload):
		self._type = msg_type
		self._payload = payload

	@classmethod
	def from_error(cls, error_msg):
		return cls('ERROR', {"msg":error_msg})

	@classmethod
	def from_info_dict(cls, info_dict):
		return cls('INFO', info_dict)

	def __repr__(self):
		return "{._type} {._payload}".format(self, self)

	def __str__(self):
		return "{._type} {._payload}".format(self, self)

	@property
	def type(self):
		return self._type
	
	@property
	def payload(self):
		return self._payload

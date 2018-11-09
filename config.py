import json

class ConfigEncoder(json.JSONEncoder):

	def default(self, obj):
		if isinstance(obj, Config):
			dict_rep = dict(obj.settings)
			return dict_rep
		else:
			return super(ConfigEncoder, self).default(obj)


class ConfigDecoder(json.JSONDecoder):

	def __init__(self, *args, **kwargs):
		super(ConfigDecoder, self).__init__(object_hook=self.object_hook, *args, **kwargs)

	def object_hook(self, obj):
		if 'cmd' in obj:
			return obj
		else:
			return Config(obj)


class Config(object):
	json_decoder = ConfigDecoder
	json_encoder = ConfigEncoder

	default_settings = {"multicast_ip":"224.0.0.150",
								"multicast_port":10000,
								"command_port":6760,
 								"rtsp_port":8554,
								"heartbeat_timeout":10.0,
								"failsafe_mission":[{"latitude": 40.599374, "altitude": 5.0, "cmd": "WAYPOINT", "longitude": -80.009048},{"cmd": "LAND"}],
								"default_takeoff_alt":2.5,
								"default_waypoint_radius":1.0,
								"default_waypoint_hold":1.0,
								"intermission":0.1,
								"mission_resend_limit":5,
								"takeoff_resend_limit":5,
								"land_resend_limit":5,
								"takeoff_timeout":2.0,
								"land_timeout":3.0,
								"min_land_delta":2.0,
								"min_takeoff_height":1.0}


	def __init__(self, settings_dict):
		# Merge supplied settings with defaults
		self._settings = Config.default_settings.copy()
		self._settings.update(settings_dict)

	def __contains__(self, key):
		return key in self._settings

	def __getitem__(self, key):
		if key in self._settings:
			return self._settings[key]
		else:
			return None

	def __setitem__(self, key, value):
		self._settings[key] = value

	@property
	def settings(self):
		return self._settings
	
	@property
	def multicast_ip(self):
		return self._settings['multicast_ip']

	@property
	def failsafe_mission(self):
		return self._settings['failsafe_mission']

import threading
import dronekit
from pymavlink import mavutil
import Queue
import time

# Default Waypoint Params
DEFAULT_RADIUS = 1.0
DEFAULT_HOLD_TIME = 1.0

# Default Failsafe Params
DEFAULT_HEARTBEAT_TIMEOUT = 20.0
DEFAULT_FAILSAFE_MISSION = [{"latitude": 40.599374, "altitude": 3.0, "cmd": "WAYPOINT", "longitude": -80.009048},{"cmd": "LAND"}]

MAV_CMD = {'TAKEOFF':mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 
				'WAYPOINT':mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
				'LAND':mavutil.mavlink.MAV_CMD_NAV_LAND,
				'MODE':mavutil.mavlink.MAV_CMD_DO_SET_MODE,
				'OVERRIDE':mavutil.mavlink.MAV_CMD_OVERRIDE_GOTO}

MAV_MODE = {'GUIDED':8, 'AUTO':4}

class DroneController(threading.Thread):

	def  __init__(self, cmd_queue):
		self._cmd_queue  = cmd_queue
		self._current_command = None
		self._is_alive = False
		self._is_interrupted = False

		# spin up drone kit, connect to mavlink stream, etc
		connection_string = 'tcp:127.0.0.1:5760'
		self._vehicle = dronekit.connect(connection_string, wait_ready=False)

		# Download vehicle commands - needed for home location
		cmds = self._vehicle.commands
		cmds.clear()
		cmds.upload()

		self._position = self._vehicle.location.global_relative_frame
		self._home = self._position

		self._target_system = self._vehicle._master.target_system
		self._target_component =  self._vehicle._master.target_component

		self._mode("GUIDED")

		self._last_heartbeat = None

		super(DroneController, self).__init__()

	def start(self):
		self._is_alive = True
		# Python 3
		#super().start()

		super(DroneController, self).start()

	def stop(self):
		self._is_alive = False

	def interrupt(self):
		self._is_interrupted = True
		current_pos = self._vehicle.location.global_relative_frame
		arg_list = [mavutil.mavlink.MAV_GOTO_DO_HOLD, mavutil.mavlink.MAV_GOTO_HOLD_AT_CURRENT_POSITION, 0, 0, current_pos.lat, current_pos.lon, current_pos.alt]
		#arg_list = [mavutil.mavlink.MAV_GOTO_DO_HOLD, mavutil.mavlink.MAV_GOTO_HOLD_AT_CURRENT_POSITION, 0, 0, 0, 0, 0]
		self._send_command(MAV_CMD['OVERRIDE'], *arg_list)

	def resume(self):
		arg_list = [mavutil.mavlink.MAV_GOTO_DO_CONTINUE, 0, 0, 0, 0, 0, 0]
		self._send_command(MAV_CMD['OVERRIDE'], *arg_list)

		self._is_interrupted = False

	def update_heartbeat(self, timestamp):
		print("Got heartbeat update")
		self._last_heartbeat = timestamp

	def _is_running(self):
		return self._is_alive and not self._is_interrupted

	def run(self):
		print("DroneController running")
		self._last_heartbeat = time.time()
		while self._is_alive:
			if self._is_interrupted:
				# process hold command
				print("Control thread interrupted")
				time.sleep(3)
			elif time.time() - self._last_heartbeat > DEFAULT_HEARTBEAT_TIMEOUT:
				print("Lost heartbeat, executing failsafe behavior")

				self._is_interrupted = True
				self._mission(DEFAULT_FAILSAFE_MISSION)

			else:
				try:
					cmd = self._cmd_queue.get(timeout=3)
				except Queue.Empty as e:
					#handle empty command queue, add autonomy here
					print("Command Queue is empty")
					cmd = None

				self._current_command = cmd

				if cmd is not None:
					self._process_command(cmd)

		self._vehicle.close()
		print("DroneController thread stopped")

	def _process_command(self, msg):
		if msg.type != 'CMD':
			print("Error tried to process a message that was not a command")
			return

		payload = msg.payload
		cmd = payload['cmd']

		cmd_func_name = "_{0}".format(cmd.lower())
		cmd_func = getattr(self, cmd_func_name, lambda **kwargs: self._error(cmd, **kwargs))

		try:
			cmd_func(**payload)
		except:
			print("An exception occurred while processing command {0}".format(msg))


	# Processes unrecognized commmands
	def _error(self, cmd, **cmd_args):
		print("Unknown command {0} with args {1}".format(cmd, cmd_args))
	
	def _mode(self, mode, **unknown_options):
		arg_list = [MAV_MODE[mode], 0, 0, 0, 0, 0, 0]
		self._send_command(MAV_CMD['MODE'], *arg_list)

	def _arm(self, **unknown_options):
		self._vehicle.armed = True

		while self._is_running() and not self._vehicle.armed:
			print("Waiting for arming...")
			time.sleep(1)
			self._vehicle.armed = True

	def _disarm(self, **unknown_options):
		self._vehicle.armed = False

		while self._is_running() and self._vehicle.armed:
			print("Waiting for disarming...")
			time.sleep(1)
			self._vehicle.armed = False

	def _takeoff(self, target_altitude=2.5, latitude=None, longitude=None, **unknown_options):
		altitude = 0.0
		# If not given a latitude and longitude, takeoff at current position
		if latitude is None or longitude is None:
			current_pos = self._vehicle.location.global_relative_frame
			latitude = current_pos.lat
			longitude = current_pos.lon
			altitude = current_pos.alt

		if latitude is not None and longitude is not None:
			arg_list = [0, 0, 0, 0, latitude, longitude, altitude + target_altitude]
			self._send_command(MAV_CMD['TAKEOFF'], *arg_list)
		else:
			print("No takeoff location specified and no GPS data available.")

	def _land(self, latitude=None, longitude=None, ground_level=0.0, **unknown_options):
		if latitude is None or longitude is None:
			# Use current location
			current_pos = self._vehicle.location.global_relative_frame
			latitude = current_pos.lat
			longitude = current_pos.lon

		if latitude is not None and longitude is not None:
			arg_list = [0, 0, 0, 0, latitude, longitude, ground_level]
			self._send_command(MAV_CMD['LAND'], *arg_list)
		else:
			print("No landing location specified and no GPS data available.")

	def _waypoint(self, latitude, longitude, altitude, radius=DEFAULT_RADIUS, hold_time=DEFAULT_HOLD_TIME, **unknown_options):
		arg_list = [hold_time, radius, 0, 0, latitude, longitude, altitude]
		self._send_command(MAV_CMD['WAYPOINT'], *arg_list)

	def _mission(self, cmd_list, **unknown_options):
		cmds = self._vehicle.commands

		cmds.clear()

		for element in cmd_list:
			if element['cmd'] == 'WAYPOINT':
				cmd = dronekit.Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, MAV_CMD['WAYPOINT'], 0, 1, 
												DEFAULT_HOLD_TIME, DEFAULT_RADIUS, 0, 0, element['latitude'], element['longitude'], element['altitude'])
				cmds.add(cmd)

			elif element['cmd'] == 'TAKEOFF':
				current_pos = self._vehicle.location.global_relative_frame
				cmd = dronekit.Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, MAV_CMD['TAKEOFF'], 0, 1, 
												0, 0, 0, 0, current_pos.lat, current_pos.lon, current_pos.alt + element['target_altitude'])
				cmds.add(cmd)

			elif element['cmd'] == 'LAND':
				current_pos = self._vehicle.location.global_relative_frame
				cmd = dronekit.Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, MAV_CMD['LAND'], 0, 1, 
												0, 0, 0, 0, current_pos.lat, current_pos.lon, current_pos.alt)
				cmds.add(cmd)

		cmds.upload()


	def _legacy_process_command(self, cmd):
		if cmd.type != 'CMD':
			print("Error tried to process a message that was not a command")
			return

		payload = cmd.payload

		if payload['cmd'] == 'ARM':
			self._px4_set_mode(MAV_MODE['GUIDED']) #Guided mode
			self._vehicle.armed = True

			while self._is_running() and not self._vehicle.armed:
				print("Waiting for arming...")
				time.sleep(1)
				self._vehicle.armed = True

		elif payload['cmd'] == 'DISARM':
			self._px4_set_mode(MAV_MODE['GUIDED']) #Guided mode
			self._vehicle.armed = False

			while self._is_running() and self._vehicle.armed:
				print("Waiting for disarming...")
				time.sleep(1)
				self._vehicle.armed = False

		elif payload['cmd'] == 'TAKEOFF':
			self._px4_set_mode(MAV_MODE['GUIDED']) #Guided mode

			if self._vehicle.armed:
				#self._vehicle.simple_takeoff(payload['target_altitude'])
				current_pos = self._vehicle.location.global_relative_frame
				arg_list = [0, 0, 0, 0, current_pos.lat, current_pos.lon, current_pos.alt + payload['target_altitude']]
				self._send_command(MAV_CMD['TAKEOFF'], *arg_list)
				
				print("taking off to target altitude {0}".format(payload['target_altitude']))
				while self._is_running() and self._vehicle.location.global_relative_frame.alt <= payload['target_altitude']*0.70:
					print("Current altitude: {0}".format(self._vehicle.location.global_relative_frame.alt))
					time.sleep(1)

				print("Takeoff complete")

		elif payload['cmd'] == 'LAND':
			self._px4_set_mode(MAV_MODE['GUIDED']) #Guided mode

			current_pos = self._vehicle.location.global_relative_frame
			
			arg_list = [0, 0, 0, 0, current_pos.lat, current_pos.lon, current_pos.alt]
			self._send_command(MAV_CMD['LAND'], *arg_list)

			time.sleep(1)

		elif payload['cmd'] == 'WAYPOINT':
			self._px4_set_mode(MAV_MODE['AUTO']) #Auto mode


			del payload['cmd']
			self._waypoint(**payload)

			#arg_list = [1, 0, 0, 0, payload['latitude'], payload['longitude'], payload['altitude']]
			#self._send_command(MAV_CMD['WAYPOINT'], *arg_list)

			time.sleep(3)

		elif payload['cmd'] == 'MISSION':
			self._px4_set_mode(MAV_MODE['AUTO']) #Auto mode

			cmds = self._vehicle.commands
			#cmds.download()
			#cmds.wait_ready()

			cmds.clear()

			for element in payload['cmd_list']:
				if element['cmd'] == 'WAYPOINT':
					cmd = dronekit.Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, MAV_CMD['WAYPOINT'], 0, 1, 
													DEFAULT_HOLD_TIME, DEFAULT_RADIUS, 0, 0, element['latitude'], element['longitude'], element['altitude'])
					cmds.add(cmd)

				elif element['cmd'] == 'TAKEOFF':
					current_pos = self._vehicle.location.global_relative_frame
					cmd = dronekit.Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, MAV_CMD['TAKEOFF'], 0, 1, 
													0, 0, 0, 0, current_pos.lat, current_pos.lon, current_pos.alt + element['target_altitude'])
					cmds.add(cmd)

				elif element['cmd'] == 'LAND':
					current_pos = self._vehicle.location.global_relative_frame
					cmd = dronekit.Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, MAV_CMD['LAND'], 0, 1, 
													0, 0, 0, 0, current_pos.lat, current_pos.lon, current_pos.alt)
					cmds.add(cmd)

			cmds.upload()
			time.sleep(1)

			
		else:
			print("Unknown command{0}".format(cmd))


	def _px4_set_mode(self, mode):
		arg_list = [mode, 0, 0, 0, 0, 0, 0]
		self._send_command(MAV_CMD['MODE'], *arg_list)

	def _send_command(self, cmd, arg1, arg2, arg3, arg4, arg5, arg6, arg7):
		self._vehicle._master.mav.command_long_send(self._target_system, self._target_component, cmd, 0,
																	arg1, arg2, arg3, arg4, arg5, arg6, arg7)
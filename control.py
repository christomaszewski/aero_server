import threading
import dronekit
from pymavlink import mavutil
from messages import Message
import Queue
import time
import logging
import sys
import os
import json

# Default system params
DEFAULT_INTERMISSION = 0.1
DEFAULT_MISSION_RESEND_LIMIT = 5
DEFAULT_TAKEOFF_RESEND_LIMIT = 5
DEFAULT_LAND_RESEND_LIMIT = 5
DEFAULT_TAKEOFF_TIMEOUT = 2.0
DEFAULT_LAND_TIMEOUT = 3.0
DEFAULT_MIN_LAND_DELTA = 2.0
DEFAULT_MIN_TAKEOFF_HEIGHT = 1.0

# Default waypoint params
DEFAULT_RADIUS = 3.0
DEFAULT_HOLD_TIME = 1.0
DEFAULT_TAKEOFF_ALT = 2.5

# Default failsafe params
DEFAULT_HEARTBEAT_TIMEOUT = 20.0
DEFAULT_FAILSAFE_MISSION = [{"latitude": 40.5993520, "altitude": 5.0, "cmd": "WAYPOINT", "longitude": -80.0092670}, {"cmd": "LAND", "latitude": 40.5993520, "longitude": -80.0092670}]

"""
FAILSAFE_CONF = '/home/aero/src/aero_server/failsafe.conf'
with open(FAILSAFE_CONF,'r') as fh:
        conf = json.load(fh)
DEFAULT_FAILSAFE_MISSION = conf['failsafe_mission']
"""
MAV_CMD = {'TAKEOFF':mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 
				'WAYPOINT':mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
				'LAND':mavutil.mavlink.MAV_CMD_NAV_LAND,
				'MODE':mavutil.mavlink.MAV_CMD_DO_SET_MODE,
				'OVERRIDE':mavutil.mavlink.MAV_CMD_OVERRIDE_GOTO,
				'ARM_DISARM':mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM}

MAV_MODE = {'GUIDED':8, 'AUTO':4}

class DroneController(threading.Thread):

	def  __init__(self, cmd_queue, response_queue, server_config):
		self._cmd_queue  = cmd_queue
		self._response_queue = response_queue
		self._server_config = server_config
		self._current_command = None
		self._is_alive = False
		self._is_interrupted = False

		self._logger = logging.getLogger('command_server_log')

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

		self._mode('GUIDED')

		self._last_heartbeat = time.time()

		super(DroneController, self).__init__()

	def start(self):
		self._is_alive = True
		# Python 3
		#super().start()

		super(DroneController, self).start()

	def stop(self):
		self._is_alive = False

	def safety_behavior(self):
		self._logger.info("Safety behavior initiated")
		self._is_interrupted = True
		self._mode('GUIDED')
		
		self._mission(self._server_config.failsafe_mission)
		#self._mission(DEFAULT_FAILSAFE_MISSION)

		# This line skips over HOME at front of mission
		#self._vehicle.commands.next = 1
		
		self._mode('AUTO')

	def interrupt(self):
		self._logger.debug("Interrupt called")
		self._is_interrupted = True
		current_pos = self._vehicle.location.global_relative_frame
		arg_list = [mavutil.mavlink.MAV_GOTO_DO_HOLD, mavutil.mavlink.MAV_GOTO_HOLD_AT_CURRENT_POSITION, 0, 0, current_pos.lat, current_pos.lon, current_pos.alt]
		#arg_list = [mavutil.mavlink.MAV_GOTO_DO_HOLD, mavutil.mavlink.MAV_GOTO_HOLD_AT_CURRENT_POSITION, 0, 0, 0, 0, 0]
		self._send_command(MAV_CMD['OVERRIDE'], *arg_list)
		self._mode('GUIDED')

	def resume(self):
		self._logger.debug("Resume called")
		arg_list = [mavutil.mavlink.MAV_GOTO_DO_CONTINUE, 0, 0, 0, 0, 0, 0]
		self._send_command(MAV_CMD['OVERRIDE'], *arg_list)
		self._mode('AUTO')
		self._is_interrupted = False

	def update_heartbeat(self, timestamp):
		self._logger.info("Got heartbeat update, time since last heartbeat: {0}".format(timestamp - self._last_heartbeat))
		self._last_heartbeat = timestamp

	def _is_running(self):
		return self._is_alive and not self._is_interrupted

	def run(self):
		self._logger.info("DroneController running")
		self._last_heartbeat = time.time()
		while self._is_alive:
			batt = self._vehicle.battery
			self._logger.info(batt)

			if self._is_interrupted:
				self._logger.info("Control thread interrupted")
				time.sleep(3)

			elif self._vehicle.armed and self._vehicle.battery.level < self._server_config.low_battery_level:
				failsafe_msg = "Low Battery, executing failsafe behavior"
				self._logger.warning(failsafe_msg)
				msg = Message("FAILSAFE", {"msg":failsafe_msg})
				self._response_queue.put(msg)

				self.safety_behavior()

			elif self._vehicle.armed and time.time() - self._last_heartbeat > self._server_config.heartbeat_timeout:
				failsafe_msg = "Lost heartbeat, executing failsafe behavior"
				self._logger.warning(failsafe_msg)
				msg = Message("FAILSAFE", {"msg":failsafe_msg})
				self._response_queue.put(msg)

				self.safety_behavior()

			else:
				try:
					cmd = self._cmd_queue.get(timeout=3)
				except Queue.Empty as e:
					#handle empty command queue, add autonomy here
					self._logger.debug("Command Queue is empty")
					cmd = None

				self._current_command = cmd
				self._logger.info("Processing command {0}".format(cmd))
				if cmd is not None:
					self._process_command(cmd)

		self._vehicle.close()
		self._logger.info("DroneController thread stopped")

	def _error(self, error_msg):
		self._logger.error(error_msg)
		msg = Message.from_error(error_msg)
		self._response_queue.put(msg)

	def _process_command(self, msg):
		if msg.type != 'CMD':
			self._logger.error("Tried to process a message that was not a command")
			return

		payload = msg.payload
		cmd = payload['cmd']

		cmd_func_name = "_{0}".format(cmd.lower())
		cmd_func = getattr(self, cmd_func_name, lambda **kwargs: self._unknown(cmd, **kwargs))

		try:
			cmd_func(**payload)
		except:
			self._error("{0} exception occurred while processing command {1}".format(sys.exc_info()[0], msg))

		time.sleep(DEFAULT_INTERMISSION)

	def _preflight(self, **unknown_options):
		self._server_config.preflight_passed = False

		if self._vehicle.battery.level < self._server_config.preflight_battery_level:
			self._error("Preflight failed due to insufficient battery level")
			return False

		if self._vehicle.gps_0.fix_type <= 1:
			self._error("Preflight failed due to lack of GPS fix")
			return False

		if not self._server_config.failsafe_confirmed:
			self._error("Preflight failed due to unconfirmed failsafe mission")
			return False

		if time.time() - self._last_heartbeat > self._server_config.heartbeat_timeout/2.0:
			self._error("Preflight failed due to old heartbeat")
			return False

		self._logger.debug("Arming vehicle")
		self._vehicle.armed = True

		time.sleep(1.5)

		if not self._vehicle.armed:
			self._error("Preflight failed due to failed arming")
			return False

		self._logger.debug("Disarming vehicle")
		self._vehicle.armed = False

		time.sleep(1.5)

		if self._vehicle.armed:
			self._error("Preflight failed due to failed disarming")
			return False

		self._server_config.preflight_passed = True

		info_dict = {"preflight_passed":True}
		msg = Message.from_info_dict(info_dict)
		self._response_queue.put(msg)

		self._logger.info("Preflight passed")

		return True

	# Processes unrecognized commmands
	def _unknown(self, cmd, **cmd_args):
		self._error("Unknown command {0} with args {1}".format(cmd, cmd_args))
	
	def _mode(self, mode, **unknown_options):
		self._logger.debug("Current Mode: {0}, Setting Mode: {1} {2}".format(self._vehicle.mode, mode, MAV_MODE[mode]))
		arg_list = [MAV_MODE[mode], 0, 0, 0, 0, 0, 0]
		self._send_command(MAV_CMD['MODE'], *arg_list)

		time.sleep(DEFAULT_INTERMISSION)

		self._logger.debug("Mode after set: {0}".format(self._vehicle.mode))

	def _raw_arm(self):
		arg_list = [1, 0, 0, 0, 0, 0, 0]
		self._send_command(MAV_CMD['ARM_DISARM'], *arg_list)

	def _arm(self, **unknown_options):
		if not self._server_config.preflight_passed:
			self._error("Arming denied, preflight not complete")
			return False
	
		self._logger.debug("Arming vehicle")
		self._vehicle.armed = True
		time.sleep(self._server_config.arm_timeout)

		send_count = 1

		while self._is_running() and not self._vehicle.armed and send_count < self._server_config.arm_resend_limit:
			self._logger.info("Vehicle still disarmed, retrying arming...")
			time.sleep(self._server_config.arm_timeout)
			self._vehicle.armed = True
			send_count += 1

		time.sleep(DEFAULT_INTERMISSION)

		# If still hasn't armed, give the raw arm command a try
		if not self._vehicle.armed:
			self._logger.info("Dronekit arming failed. Attempting to send a raw arm command")
			self._raw_arm()
			self._vehicle.armed = True

		time.sleep(self._server_config.arm_timeout)

		if self._vehicle.armed:
			self._logger.debug("Vehicle armed")
			return True
		else:
			self._error("Failed to arm vehicle after {0} attempts".format(send_count))
			return False

	def _raw_disarm(self):
		arg_list = [0, 0, 0, 0, 0, 0, 0]
		self._send_command(MAV_CMD['ARM_DISARM'], *arg_list)
		
	def _disarm(self, **unknown_options):
		self._logger.debug("Disarming vehicle")
		self._vehicle.armed = False
		time.sleep(self._server_config.arm_timeout)

		send_count = 1

		while self._is_running() and self._vehicle.armed and send_count < self._server_config.arm_resend_limit:
			self._logger.info("Vehicle still armed, retrying disarm...")
			time.sleep(self._server_config.arm_timeout)
			self._vehicle.armed = False
			send_count += 1

		time.sleep(DEFAULT_INTERMISSION)

		# If still hasn't disarmed, give the raw disarm command a try
		if not self._vehicle.armed:
			self._logger.info("Dronekit disarming failed. Attempting to send a raw disarm command")
			self._raw_disarm()
			self._vehicle.armed = False

		time.sleep(self._server_config.arm_timeout)

		if not self._vehicle.armed:
			self._logger.debug("Vehicle disarmed, Clearing mission")
			cmds = self._vehicle.commands
			cmds.clear()
			cmds.upload()
			return True
		else:
			self._error("Failed to disarm vehicle after {0} attempts".format(send_count))
			return False

	def _takeoff_sender(self, latitude, longitude, altitude):
		self._logger.info("Taking off to {0} meters above {1},{2}".format(altitude, latitude, longitude))
		arg_list = [0, 0, 0, 0, latitude, longitude, altitude]
		self._send_command(MAV_CMD['TAKEOFF'], *arg_list)

	def _takeoff(self, target_altitude=2.5, latitude=None, longitude=None, **unknown_options):
		takeoff_complete = False		
		altitude = 0.0
		# If not given a latitude and longitude, takeoff at current position
		if latitude is None or longitude is None:
			current_pos = self._vehicle.location.global_relative_frame
			latitude = current_pos.lat
			longitude = current_pos.lon
			altitude = current_pos.alt

		if latitude is not None and longitude is not None:
			send_count = 0		

			while not takeoff_complete and send_count < self._server_config.takeoff_resend_limit:
				self._takeoff_sender(latitude, longitude, altitude+target_altitude)
				send_count += 1
				time.sleep(self._server_config.takeoff_timeout)				
				takeoff_complete = self._vehicle.location.global_relative_frame.alt >= self._server_config.min_takeoff_height
				if takeoff_complete:
					self._logger.info("Takeoff successful")
				elif send_count < self._server_config.takeoff_resend_limit:
					self._logger.warning("Failed to reach minimum takeoff altitude of {0} meters, retrying takeoff command {1}".format(self._server_config.min_takeoff_height, send_count))
				else:
					self._error("Failed to takeoff after {0} attempts".format(self._server_config.takeoff_resend_limit))

		else:
			self._error("Ignoring TAKEOFF command - No takeoff location specified and no GPS data available.")

		time.sleep(DEFAULT_INTERMISSION)
		return takeoff_complete

	def _land_sender(self, latitude, longitude, ground_level):
		self._logger.info("Landing at {0},{1}".format(latitude,longitude))
		arg_list = [0, 0, 0, 0, latitude, longitude, ground_level]
		self._send_command(MAV_CMD['LAND'], *arg_list)		

	def _land(self, latitude=None, longitude=None, ground_level=0.0, **unknown_options):
		landing_complete = False	
		if latitude is None or longitude is None:
			# Use current location
			current_pos = self._vehicle.location.global_relative_frame
			latitude = current_pos.lat
			longitude = current_pos.lon

		if latitude is not None and longitude is not None:
			last_altitude = self._vehicle.location.global_relative_frame.alt
			send_count = 0

			while not landing_complete and send_count < self._server_config.land_resend_limit:
				self._land_sender(latitude, longitude, ground_level)
				send_count += 1
				time.sleep(self._server_config.land_timeout)
				landing_complete = last_altitude - self._vehicle.location.global_relative_frame.alt >= self._server_config.min_land_delta
				if landing_complete:
					self._logger.info("Landing successfully initiated")
				elif send_count < self._server_config.land_resend_limit:
					self._logger.warning("Failed to initiate landing, retrying land command {0}".format(send_count))
				else:
					self._error("Failed to initiate landing after {0} attempts".format(self._server_config.land_resend_limit))
			
		else:
			self._error("Ignoring LAND command - No landing location specified and no GPS data available.")

		time.sleep(DEFAULT_INTERMISSION)
		return landing_complete

	def _waypoint(self, latitude, longitude, altitude, radius=DEFAULT_RADIUS, hold_time=DEFAULT_HOLD_TIME, **unknown_options):
		arg_list = [hold_time, radius, 0, 0, latitude, longitude, altitude]
		self._send_command(MAV_CMD['WAYPOINT'], *arg_list)
		time.sleep(DEFAULT_INTERMISSION)

	def _mission_sender(self, cmd_list):
		cmds = self._vehicle.commands
		cmds.clear()

		last_command_location = None

		for element in cmd_list:
			self._logger.info("Parsing mission element {0}".format(element))
			if 'cmd' not in element:
				self._error("Rejecting Mission - Malformed mission element (cmd not found): {0}".format(element))
				cmds.clear()
				break
			
			elif element['cmd'] == 'WAYPOINT':
				self._logger.debug("Parsing WAYPOINT mission element")
				lat = None
				lon = None
				alt = None

				if 'latitude' in element:
					lat = element['latitude']

				if 'longitude' in element:
					lon = element['longitude']

				if 'altitude' in element:
					alt = element['altitude']
				elif last_command_location is not None:
					alt = last_command_location[2]
				else:
					alt = self._vehicle.location.global_relative_frame.alt


				if lat is None or lon is None or alt is None:
					self._error("Rejecting Mission - Malformed mission element WAYPOINT (missing lat, long, or alt): {0}".format(element))
					cmds.clear()
					break

				last_command_location = (lat, lon, alt)
				cmd = dronekit.Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, MAV_CMD['WAYPOINT'], 0, 1, 
												DEFAULT_HOLD_TIME, DEFAULT_RADIUS, 0, 0, lat, lon, alt)
				cmds.add(cmd)

			elif element['cmd'] == 'TAKEOFF':
				self._logger.debug("Parsing TAKEOFF mission element")
				target_alt = DEFAULT_TAKEOFF_ALT

				if target_alt in element:
					target_alt = element['target_altitude']

				current_pos = self._vehicle.location.global_relative_frame
				last_command_location = (current_pos.lat, current_pos.lon, current_pos.alt + target_alt)
				cmd = dronekit.Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, MAV_CMD['TAKEOFF'], 0, 1, 
												0, 0, 0, 0, current_pos.lat, current_pos.lon, current_pos.alt + target_alt)
				cmds.add(cmd)

			elif element['cmd'] == 'LAND':
				self._logger.debug("Parsing LAND mission element")
				lat = None
				lon = None

				if 'latitude' in element:
					lat = element['latitude']
				elif last_command_location is not None:
					lat = last_command_location[0]

				if 'longitude' in element:
					lon = element['longitude']
				elif last_command_location is not None:
					lon = last_command_location[1]
				
				if lat is None or lon is None:
					current_pos = self._vehicle.location.global_relative_frame
					lat = current_pos.lat
					lon = current_pos.lon

				cmd = dronekit.Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, MAV_CMD['LAND'], 0, 1, 
												0, 0, 0, 0, lat, lon, 0.0)
				cmds.add(cmd)
		
		self._logger.info("Mission parsed, sending mission to flight controller")

		upload_successful = cmds.upload()
		return upload_successful

	def _mission(self, cmd_list, **unknown_options):
		mission_sent = False
		send_count = 0

		while not mission_sent and send_count < self._server_config.mission_resend_limit:
			mission_sent = self._mission_sender(cmd_list)
			send_count += 1

			if not mission_sent:
				self._logger.warning("Unable to upload mission, retrying {0}".format(send_count))
			else:
				self._logger.info("Mission sent to flight controller successfully")

			time.sleep(DEFAULT_INTERMISSION)

		if not mission_sent:
			self._error("An error occurred during multiple attempts to upload mission, rejecting mission")

		time.sleep(DEFAULT_INTERMISSION)

		return mission_sent

	def _send_command(self, cmd, arg1, arg2, arg3, arg4, arg5, arg6, arg7):
		self._vehicle._master.mav.command_long_send(self._target_system, self._target_component, cmd, 0,
																	arg1, arg2, arg3, arg4, arg5, arg6, arg7)

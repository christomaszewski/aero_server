import threading
import dronekit
from pymavlink import mavutil
import Queue
import time

PX4_GUIDED = 8
PX4_AUTO = 4

MAV_CMD = {'TAKEOFF':mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 
				'WAYPOINT':mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
				'LAND':mavutil.mavlink.MAV_CMD_NAV_LAND,
				'MODE':mavutil.mavlink.MAV_CMD_DO_SET_MODE,
				'OVERRIDE':mavutil.mavlink.MAV_CMD_OVERRIDE_GOTO}

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
		cmds.download()
		cmds.wait_ready()

		# Get the home location
		self._home = self._vehicle.home_location
		self._position = self._vehicle.location.global_relative_frame

		self._target_system = self._vehicle._master.target_system
		self._target_component =  self._vehicle._master.target_component

		self._px4_set_mode(PX4_GUIDED)

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

	def _is_running(self):
		return self._is_alive and not self._is_interrupted

	def run(self):
		print("DroneController running")
		while self._is_alive:
			if self._is_interrupted:
				# process hold command
				print("Control thread interrupted")
				time.sleep(3)
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

	def _process_command(self, cmd):
		if cmd.type != 'CMD':
			print("Error tried to process a message that was not a command")
			return

		payload = cmd.payload

		if payload['cmd'] == 'ARM':
			self._px4_set_mode(PX4_GUIDED) #Guided mode
			self._vehicle.armed = True

			while self._is_running() and not self._vehicle.armed:
				print("Waiting for arming...")
				time.sleep(1)
				self._vehicle.armed = True

		elif payload['cmd'] == 'DISARM':
			self._px4_set_mode(PX4_GUIDED) #Guided mode
			self._vehicle.armed = False

			while self._is_running() and self._vehicle.armed:
				print("Waiting for disarming...")
				time.sleep(1)
				self._vehicle.armed = False

		elif payload['cmd'] == 'TAKEOFF':
			self._px4_set_mode(PX4_GUIDED) #Guided mode

			if self._vehicle.armed:
				#self._vehicle.simple_takeoff(payload['target_altitude'])
				current_pos = self._vehicle.location.global_relative_frame
				arg_list = [1, 0, 0, 0, current_pos.lat, current_pos.lon, current_pos.alt + payload['target_altitude']]
				self._send_command(MAV_CMD['TAKEOFF'], *arg_list)
				
				print("taking off to target altitude {0}".format(payload['target_altitude']))
				while self._is_running() and self._vehicle.location.global_relative_frame.alt <= payload['target_altitude']*0.90:
					print("Current altitude: {0}".format(self._vehicle.location.global_relative_frame.alt))
					time.sleep(1)

				print("Takeoff complete")

		elif payload['cmd'] == 'LAND':
			self._px4_set_mode(PX4_GUIDED) #Guided mode

			current_pos = self._vehicle.location.global_relative_frame
			
			arg_list = [1, 0, 0, 0, current_pos.lat, current_pos.lon, current_pos.alt]
			self._send_command(MAV_CMD['LAND'], *arg_list)

			time.sleep(1)

		elif payload['cmd'] == 'WAYPOINT':

			self._px4_set_mode(PX4_AUTO) #Auto mode
			arg_list = [1, 0, 0, 0, payload['latitude'], payload['longitude'], payload['altitude']]
			self._send_command(MAV_CMD['WAYPOINT'], *arg_list)

			time.sleep(3)

		elif payload['cmd'] == 'MISSION':
			self._px4_set_mode(PX4_AUTO) #Auto mode

			cmds = self._vehicle.commands
			cmds.download()
			cmds.wait_ready()

			cmds.clear()

			for element in payload['cmd_list']:
				if element['cmd'] == 'WAYPOINT':
					cmd = dronekit.Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, MAV_CMD['WAYPOINT'], 0, 1, 
													0, 0, 0, 0, element['latitude'], element['longitude'], element['altitude'])
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
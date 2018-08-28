import threading
import dronekit
from pymavlink import mavutil
import Queue
import time

class DroneController(threading.Thread):

	def  __init__(self, cmd_queue):
		self._cmd_queue  = cmd_queue
		self._is_alive = False
		
		# spin up drone kit, connect to mavlink stream, etc
		connection_string = 'tcp:127.0.0.1:5760'
		self._vehicle = dronekit.connect(connection_string, wait_ready=False)
		self._px4_set_mode(8) #Guided mode

		super(DroneController, self).__init__()

	def start(self):
		self._is_alive = True
		# Python 3
		#super().start()

		super(DroneController, self).start()

	def stop(self):
		self._is_alive = False

	def run(self):
		print("DroneController running")
		while self._is_alive:
			try:
				cmd = self._cmd_queue.get(timeout=3)
			except Queue.Empty as e:
				#handle empty command queue, add autonomy here
				print("Command Queue is empty")
				cmd = None

			if cmd is not None:
				self._process_command(cmd)

		self._vehicle.close()
		print("DroneController stopped")

 	def _process_command(self, cmd):
 		if cmd.type != 'CMD':
 			print("Error tried to process a message that was not a command")
 			return

 		payload = cmd.payload

 		if payload['cmd'] == 'ARM_DISARM' and payload['value'] == 'ARM':
 			self._px4_set_mode(8) #Guided mode
 			self._vehicle.armed = True

 			while self._is_alive and not self._vehicle.armed:
 				print("Waiting for arming...")
 				time.sleep(1)
 				self._vehicle.armed = True

 		elif payload['cmd'] == 'ARM_DISARM' and payload['value'] == 'DISARM':
 			self._px4_set_mode(8) #Guided mode
 			self._vehicle.armed = False

 			while self._is_alive and self._vehicle.armed:
 				print("Waiting for disarming...")
 				time.sleep(1)
 				self._vehicle.armed = False

 		elif payload['cmd'] == 'TAKEOFF':
 			self._px4_set_mode(8) #Guided mode

 			if self._vehicle.armed:
 				#self._vehicle.simple_takeoff(payload['target_altitude'])
 				current_pos = self._vehicle.location.global_relative_frame
 				self._vehicle._master.mav.command_long_send(self._vehicle._master.target_system, self._vehicle._master.target_component,
 																	mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0,
 																	1, 0, 0, 0, current_pos.lat, current_pos.lon, current_pos.alt + payload['target_altitude'])
 				print("taking off to target altitude {0}".format(payload['target_altitude']))
 				while self._is_alive and self._vehicle.location.global_relative_frame.alt <= payload['target_altitude']*0.90:
 					print("Current altitude: {0}".format(self._vehicle.location.global_relative_frame.alt))
 					time.sleep(1)

 				print("Takeoff complete")

 		elif payload['cmd'] == 'LAND':
 			self._px4_set_mode(8) #Guided mode

 			current_pos = self._vehicle.location.global_relative_frame
 			self._vehicle._master.mav.command_long_send(self._vehicle._master.target_system, self._vehicle._master.target_component,
 																	mavutil.mavlink.MAV_CMD_NAV_LAND, 0,
 																	1, 0, 0, 0, current_pos.lat, current_pos.lon, current_pos.alt)
 			time.sleep(1)

 		elif payload['cmd'] == 'WAYPOINT':
 			wp_lat = payload['LATITUDE']
 			wp_lon = payload['LONGITUDE']
 			wp_alt = payload['ALTITUDE']

 			self._px4_set_mode(4) #Guided mode
 			self._vehicle._master.mav.command_long_send(self._vehicle._master.target_system, self._vehicle._master.target_component,
														mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0,
														1, 0, 0, 0, wp_lat, wp_lon, wp_alt)

 			time.sleep(3)

  			
 		else:
 			print("Unknown command{0}".format(cmd))

 	def _px4_set_mode(self, mode):
 		self._vehicle._master.mav.command_long_send(self._vehicle._master.target_system, self._vehicle._master.target_component,
 																	mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
 																	mode, 0, 0, 0, 0, 0, 0)
import threading
import dronekit
import Queue
import time

class DroneController(threading.Thread):

	def  __init__(self, cmd_queue):
		self._cmd_queue  = cmd_queue
		self._is_alive = False
		
		# spin up drone kit, connect to mavlink stream, etc
		connection_string = 'tcp:127.0.0.1:5760'
		self._vehicle = dronekit.connect(connection_string, wait_ready=False)
		self._vehicle.mode = dronekit.VehicleMode('GUIDED')

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
 			self._vehicle.armed = True

 			while not self._vehicle.armed:
 				print("Waiting for arming...")
 				time.sleep(1)
 		elif payload['cmd'] == 'ARM_DISARM' and payload['value'] == 'DISARM':
 			self._vehicle.armed = False

 			while self._vehicle.armed:
 				print("Waiting for disarming...")
 				time.sleep(1)

 		else:
 			print("Unknown command{0}".format(cmd))
until ./telemetry.py; do
	echo "Telemetry.py crashed with exit code $?. Respawning" >&2
done

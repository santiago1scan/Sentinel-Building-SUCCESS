#!/bin/bash
# Ejecuta el simulador en modo bridge: las lecturas van al bridge por HTTP
# y solo el bridge se conecta al backend (REST y MQTT).

(
  sleep 2
  echo "status"
) | python mqtt_sensor_simulator.py --bridge-url http://bridge:8766 --interval 30 --data-dir /app/data_sensor_simulator

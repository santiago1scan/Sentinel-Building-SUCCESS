#!/bin/bash
# Script para ejecutar el simulador en modo automático publicando por MQTT

(
  sleep 2
  echo "mqtt on"
  sleep 1
  echo "bridge1 on"
  sleep 1
  echo "lora1 on"
  sleep 1
  echo "status"
) | python mqtt_sensor_simulator.py --host mosquitto --port 1883 --interval 30 --data-dir /app/data_sensor_simulator

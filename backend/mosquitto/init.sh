#!/bin/sh
# Crea la base de dynamic-security (data/dynamic-security.json) con la cuenta de administración.
# Ejecutar UNA sola vez, antes de levantar el broker. No sobrescribe una base existente.
#
#   MQTT_ADMIN_PASSWORD='...' ./init.sh
set -eu

: "${MQTT_ADMIN_PASSWORD:?Define MQTT_ADMIN_PASSWORD con la contraseña de la cuenta admin}"

HERE="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$HERE/data"
mkdir -p "$DATA_DIR"

if [ -e "$DATA_DIR/dynamic-security.json" ]; then
  echo "Ya existe $DATA_DIR/dynamic-security.json; no se reinicializa." >&2
  exit 1
fi

printf '%s\n%s\n' "$MQTT_ADMIN_PASSWORD" "$MQTT_ADMIN_PASSWORD" | docker run --rm -i \
  -v "$DATA_DIR:/mosquitto/data" \
  --entrypoint mosquitto_ctrl eclipse-mosquitto:2.0 \
  dynsec init /mosquitto/data/dynamic-security.json admin

echo "Base dynamic-security creada en $DATA_DIR. Puedes levantar el broker."

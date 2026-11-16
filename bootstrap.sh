#!/bin/sh
# Prepara el broker MQTT de Sentinel y levanta todo el backend con docker compose.
# Es seguro volver a ejecutarlo: cada paso se omite si ya está hecho.
#
#   ./bootstrap.sh
#
# Requiere el .env de la raíz con MQTT_ADMIN_PASSWORD y MQTT_CONSUMER_PASSWORD.
set -eu

ROOT="$(cd "$(dirname "$0")" && pwd)"
MOSQ="$ROOT/backend/mosquitto"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "Falta $ROOT/.env. Copia .env.example y completa los valores." >&2
  exit 1
fi

# Carga las variables del .env en el entorno de este script y de los comandos que llama.
set -a
. ./.env
set +a

: "${MQTT_ADMIN_PASSWORD:?Define MQTT_ADMIN_PASSWORD en el .env de la raíz}"
: "${MQTT_CONSUMER_PASSWORD:?Define MQTT_CONSUMER_PASSWORD en el .env de la raíz}"
MQTT_CONSUMER_USERNAME="${MQTT_CONSUMER_USERNAME:-escucha-consumer}"
export MQTT_CONSUMER_USERNAME

# 1. Certificados TLS (gen-certs.sh no sobrescribe los existentes)
if [ -f "$MOSQ/certs/server.crt" ]; then
  echo "[1/4] Certificados TLS: ya existen"
else
  echo "[1/4] Generando certificados TLS"
  "$MOSQ/gen-certs.sh"
fi

# 2. Base de dynamic-security (init.sh se niega si ya existe)
if [ -e "$MOSQ/data/dynamic-security.json" ]; then
  echo "[2/4] Base de seguridad del broker: ya existe"
else
  echo "[2/4] Creando base de seguridad del broker"
  "$MOSQ/init.sh"
fi

# 3. Broker
echo "[3/4] Levantando el broker"
docker compose up -d mosquitto

# 4. Cuenta del consumidor de escucha (si existe, actualiza su contraseña).
# --build asegura que la imagen tenga el código actual, incluido app/scripts.
echo "[4/4] Creando o actualizando la cuenta del consumidor"
docker compose run --rm --build \
  -e MQTT_CONSUMER_USERNAME \
  -e MQTT_CONSUMER_PASSWORD \
  monolito-consulta python -m app.scripts.provision_consumer

# Resto del backend: escucha, consulta, bridge y simulador. --build reconstruye las imágenes
# con el código actual; el simulador habla solo con el bridge (no necesita credenciales MQTT).
echo "Levantando escucha, consulta, bridge y simulador"
docker compose up -d --build

echo "Estado de los servicios:"
docker compose ps

echo "Listo."

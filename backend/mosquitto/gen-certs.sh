#!/bin/sh
# Genera la CA y el certificado del servidor del broker (TLS) en backend/mosquitto/certs/.
# Es para desarrollo y pruebas; en producción usa certificados emitidos por tu CA.
#
#   ./gen-certs.sh                       # SAN: localhost, mosquitto, 127.0.0.1
#   MQTT_CERT_HOSTS="broker.ejemplo.com,10.0.0.5" ./gen-certs.sh
#
# Archivos:
#   ca.crt      Certificado de la CA. Se entrega a los clientes (nodos, bridge, backends).
#   ca.key      Llave de la CA. No se distribuye.
#   server.crt  Certificado del broker, firmado por la CA.
#   server.key  Llave privada del broker.
#
# No sobrescribe certificados existentes: bórralos a mano para regenerarlos.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
CERT_DIR="$HERE/certs"
DAYS="${MQTT_CERT_DAYS:-825}"
HOSTS="${MQTT_CERT_HOSTS:-localhost,mosquitto,127.0.0.1}"

if [ -e "$CERT_DIR/ca.crt" ] || [ -e "$CERT_DIR/server.crt" ]; then
  echo "Ya existen certificados en $CERT_DIR; no se regeneran." >&2
  exit 1
fi
mkdir -p "$CERT_DIR"

# subjectAltName: IPs como IP:x, nombres como DNS:x.
SAN=""
OLD_IFS="$IFS"; IFS=","
for host in $HOSTS; do
  case "$host" in
    *[!0-9.]*|"") entry="DNS:$host" ;;
    *) entry="IP:$host" ;;
  esac
  SAN="${SAN:+$SAN,}$entry"
done
IFS="$OLD_IFS"

CN="${HOSTS%%,*}"

openssl genrsa -out "$CERT_DIR/ca.key" 4096 2>/dev/null
openssl req -x509 -new -nodes -key "$CERT_DIR/ca.key" -sha256 -days 3650 \
  -subj "/O=Sentinel Building/CN=Sentinel Dev CA" -out "$CERT_DIR/ca.crt"

openssl genrsa -out "$CERT_DIR/server.key" 2048 2>/dev/null
openssl req -new -key "$CERT_DIR/server.key" -subj "/O=Sentinel Building/CN=$CN" \
  -out "$CERT_DIR/server.csr"

EXT="$CERT_DIR/server.ext"
printf 'subjectAltName=%s\nbasicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n' "$SAN" > "$EXT"
openssl x509 -req -in "$CERT_DIR/server.csr" -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" \
  -CAcreateserial -out "$CERT_DIR/server.crt" -days "$DAYS" -sha256 -extfile "$EXT" 2>/dev/null

rm -f "$CERT_DIR/server.csr" "$EXT" "$CERT_DIR/ca.srl"

# El broker corre como usuario "mosquitto" dentro del contenedor: debe poder leer la llave.
# La carpeta certs/ no se versiona y se monta en solo lectura.
chmod 644 "$CERT_DIR/ca.crt" "$CERT_DIR/server.crt" "$CERT_DIR/server.key"
chmod 600 "$CERT_DIR/ca.key"

echo "Certificados creados en $CERT_DIR (SAN: $SAN)."

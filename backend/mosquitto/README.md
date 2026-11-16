# Broker Mosquitto de Sentinel

Broker MQTT **solo sobre TLS**, con autenticación y permisos por nodo mediante el plugin
**dynamic-security** que viene incluido en la imagen oficial `eclipse-mosquitto:2.0`
(verificado en 2.0.22). No hace falta una imagen propia.

## Modelo de acceso

| Cliente | Credencial | Permiso |
|---|---|---|
| Cada nodo (`NODE-FLOOR-1`, …) | Usuario = código del nodo, contraseña = su token | Publicar solo en `sentinel/v1/{edificio}/{nodo}/telemetry/aggregate` |
| Consumidor de escucha (`escucha-consumer`) | Usuario y contraseña propios | Suscribirse a `sentinel/v1/+/+/telemetry/aggregate` |
| Administración (`admin`) | Contraseña de `init.sh` | Administrar clientes y roles (lo usa el backend de consulta) |

- Un cliente sin credenciales válidas no conecta (`allow_anonymous false`).
- **Solo existe el puerto 8883 (TLS 1.2+).** No hay listener en claro ni WebSocket: el token del nodo
  nunca viaja sin cifrar y una conexión sin TLS es rechazada.
- Los clientes validan el certificado del broker con la CA (`certs/ca.crt`); un certificado de otra CA
  se rechaza.
- Cada nodo tiene **su propio rol** con un topic **literal**. Un comodín o `%u` en el ACL de publicación no entrega mensajes en esta versión, así que no se usan.
- Las contraseñas se guardan con hash PBKDF2-HMAC-SHA512 (con sal) en `data/dynamic-security.json`, no en claro.
- Revocar un nodo = `disableClient`: impide nuevas conexiones y corta la sesión activa.
- Los intentos rechazados quedan en el log del broker (`docker compose logs mosquitto`):
  `Client <id> disconnected, not authorised.` para credenciales inválidas o revocadas, y
  `OpenSSL Error ...` / `Protocol error` para conexiones sin TLS o con TLS fallido. El log del broker
  no incluye el usuario del intento rechazado, solo el identificador del cliente.

## Archivos

| Archivo | Para qué |
|---|---|
| `mosquitto.conf` | Configuración del broker: plugin, anónimos cerrados, listener 8883 con TLS |
| `gen-certs.sh` | Genera la CA y el certificado del broker en `certs/` (desarrollo y pruebas) |
| `init.sh` | Crea la base `data/dynamic-security.json` con la cuenta admin. Se ejecuta una vez |
| `verify_dynsec.py` | Verifica el broker en vivo (TLS, autenticación, ACL por nodo, revocación) con clientes `VERIFY-*` |
| `certs/` | CA y llaves TLS. Está en `.gitignore`: contiene llaves privadas |
| `data/` | Estado del broker. Está en `.gitignore`: contiene hashes y no se versiona |

## Puesta en marcha

Todo se ejecuta una sola vez, antes del primer `docker compose up`.

1. Generar los certificados TLS (el SAN incluye `localhost`, `mosquitto` y `127.0.0.1`; para otros
   hosts usa `MQTT_CERT_HOSTS="broker.ejemplo.com,10.0.0.5" ./gen-certs.sh`):

   ```bash
   cd backend/mosquitto
   ./gen-certs.sh
   ```

2. Inicializar la base de dynamic-security con la contraseña del administrador:

   ```bash
   MQTT_ADMIN_PASSWORD='contraseña-admin-fuerte' ./init.sh
   ```

3. Definir en el `.env` de la raíz (ver `.env.example`) la misma contraseña de administración y la del
   consumidor de escucha:

   ```
   MQTT_ADMIN_PASSWORD=contraseña-admin-fuerte
   MQTT_CONSUMER_USERNAME=escucha-consumer
   MQTT_CONSUMER_PASSWORD=contraseña-consumidor
   ```

4. Levantar el broker y crear la cuenta del consumidor de escucha (idempotente; sirve también para
   cambiar su contraseña):

   ```bash
   cd ../..                       # raíz del repositorio
   set -a; . ./.env; set +a       # carga las variables del .env en el shell
   docker compose up -d mosquitto
   docker compose run --rm -e MQTT_CONSUMER_USERNAME -e MQTT_CONSUMER_PASSWORD \
     monolito-consulta python -m app.scripts.provision_consumer
   ```

5. Dar de alta los clientes de los nodos que **ya existían** (verifica cada token contra el hash de la BD):

   ```bash
   docker compose run --rm -e SENTINEL_NODE_TOKENS \
     monolito-consulta python -m app.scripts.provision_existing_nodes
   ```

   Hace falta `SENTINEL_NODE_TOKENS` en el `.env` de la raíz (`NODE-FLOOR-1=token1,NODE-FLOOR-2=token2`).
   Los nodos nuevos se registran por solicitud (`POST /registrations`, aprobación del administrador y
   entrega del token): su cliente en el broker se crea al entregar el token.

6. Levantar el resto del stack:

   ```bash
   docker compose up -d
   ```

7. Verificar el broker (desde el host, con `pip install "paho-mqtt>=2.1,<3"`):

   ```bash
   MQTT_ADMIN_PASSWORD='contraseña-admin-fuerte' python verify_dynsec.py \
     --host localhost --port 8883 --cafile certs/ca.crt
   ```

   Debe mostrar `15/15 checks ok`.

## Cómo se conectan los servicios

El `compose.yaml` monta `certs/ca.crt` en `/certs/ca.crt` de cada servicio y los configura así:

| Servicio | Variables / opciones | Cuenta |
|---|---|---|
| `monolito-escucha` | `MQTT_HOST`, `MQTT_PORT=8883`, `MQTT_TLS=true`, `MQTT_CA_FILE`, `MQTT_USERNAME`, `MQTT_PASSWORD` | `escucha-consumer` |
| `monolito-consulta` | `MQTT_HOST`, `MQTT_PORT=8883`, `MQTT_TLS=true`, `MQTT_CA_FILE`, `MQTT_ADMIN_USERNAME`, `MQTT_ADMIN_PASSWORD` | `admin` |
| `bridge` | `--mqtt-port 8883 --mqtt-tls --mqtt-ca-file /certs/ca.crt` y `SENTINEL_NODE_TOKENS` | una conexión por nodo (usuario = código, contraseña = token) |

## Producción

`gen-certs.sh` crea una CA de desarrollo. En producción usa un certificado emitido por una CA de
confianza (o la CA de la organización), reemplaza `certs/server.crt`, `certs/server.key` y `certs/ca.crt`,
y distribuye esa CA a los nodos. El certificado debe incluir en el SAN el host con el que se conectan
los clientes.

## Limitaciones conocidas

- `init.sh` imprime texto de uso de `mosquitto_ctrl` en stderr aunque la base se crea bien.
- Al montar `mosquitto.conf` y `certs/` como solo lectura, el entrypoint de la imagen muestra avisos de
  `chown` que no afectan el funcionamiento.
- `certs/server.key` queda con permiso de lectura para todos (`644`) porque el broker corre como otro
  usuario dentro del contenedor. La carpeta no se versiona; no uses este esquema tal cual en producción.
- Si el alta de un nodo en el broker falla después de insertarlo en la BD, la petición se revierte completa (la fila del nodo tampoco se guarda).
- La API REST (`/telemetry/aggregate`, `X-Node-Token`) sigue en HTTP plano. El cifrado de esa ruta es
  independiente del broker MQTT y no está resuelto aquí.

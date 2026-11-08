# Broker Mosquitto de Sentinel

Broker MQTT con autenticación y permisos por nodo, usando el plugin **dynamic-security** que
viene incluido en la imagen oficial `eclipse-mosquitto:2.0` (verificado en 2.0.22). No hace falta
una imagen propia.

## Modelo de acceso

| Cliente | Credencial | Permiso |
|---|---|---|
| Cada nodo (`NODE-FLOOR-1`, …) | Usuario = código del nodo, contraseña = su token | Publicar solo en `sentinel/v1/{edificio}/{nodo}/telemetry/aggregate` |
| Consumidor de escucha (`escucha-consumer`) | Usuario y contraseña propios | Suscribirse a `sentinel/v1/+/+/telemetry/aggregate` |
| Administración (`admin`) | Contraseña de `init.sh` | Administrar clientes y roles (lo usa el backend de consulta) |

- Un cliente sin credenciales válidas no conecta (`allow_anonymous false`).
- Cada nodo tiene **su propio rol** con un topic **literal**. Un comodín o `%u` en el ACL de publicación no entrega mensajes en esta versión, así que no se usan.
- Las contraseñas se guardan con hash PBKDF2-HMAC-SHA512 (con sal) en `data/dynamic-security.json`, no en claro.
- Revocar un nodo = `disableClient`: impide nuevas conexiones y corta la sesión activa.

## Archivos

| Archivo | Para qué |
|---|---|
| `mosquitto.conf` | Configuración del broker: plugin, anónimos cerrados, listener 1883 |
| `init.sh` | Crea la base `data/dynamic-security.json` con la cuenta admin. Se ejecuta una vez |
| `verify_dynsec.py` | Verifica el broker en vivo (autenticación, ACL por nodo, revocación) con clientes `VERIFY-*` |
| `data/` | Estado del broker. Está en `.gitignore`: contiene hashes y no se versiona |

## Puesta en marcha

1. Inicializar la base (una sola vez):

   ```bash
   cd backend/mosquitto
   MQTT_ADMIN_PASSWORD='contraseña-admin-fuerte' ./init.sh
   ```

2. Configurar el backend de consulta (`backend/monolito-consulta/.env`):

   ```
   MQTT_HOST=mosquitto
   MQTT_PORT=1883
   MQTT_ADMIN_USERNAME=admin
   MQTT_ADMIN_PASSWORD=contraseña-admin-fuerte
   BUILDING_CODE=SB-001
   ```

3. Configurar el consumidor de escucha (`backend/monolito-escucha/.env`), con la cuenta que se haya creado para él:

   ```
   MQTT_USERNAME=escucha-consumer
   MQTT_PASSWORD=...
   ```

4. Dar de alta los clientes de los nodos que **ya existían** (verifica cada token contra el hash de la BD):

   ```bash
   cd backend/monolito-consulta
   SENTINEL_NODE_TOKENS="$(grep ^SENTINEL_NODE_TOKENS ../../.env | cut -d= -f2-)" \
     python -m app.scripts.provision_existing_nodes
   ```

   Los nodos nuevos se dan de alta solos: `POST /nodes` crea su cliente en el broker.

5. Verificar el broker antes de usarlo con el stack:

   ```bash
   MQTT_ADMIN_PASSWORD='contraseña-admin-fuerte' python verify_dynsec.py --host localhost --port 1883
   ```

   Debe mostrar `13/13 checks ok`. Para este script hace falta `pip install "paho-mqtt>=2.1,<3"`.

## Estado actual

- La configuración y el backend ya están en el repositorio.
- **El `docker-compose` de la raíz todavía usa el broker anónimo** (`/mosquitto.conf`). Cambiarlo a `backend/mosquitto/` cierra el acceso anónimo y el 1883 de forma inmediata: hay que hacer los pasos 1 a 4 antes.
- **Pendiente:** TLS (puerto 8883 y certificados). Sin TLS, el token viaja en claro en el CONNECT del nodo.

## Limitaciones conocidas

- `init.sh` imprime texto de uso de `mosquitto_ctrl` en stderr aunque la base se crea bien.
- Al montar `mosquitto.conf` como solo lectura, el entrypoint de la imagen muestra un aviso de `chown` que no afecta el funcionamiento.
- Si el alta de un nodo en el broker falla después de insertarlo en la BD, la petición se revierte completa (la fila del nodo tampoco se guarda).

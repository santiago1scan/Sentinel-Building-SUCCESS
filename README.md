# Sentinel Building

Sistema de monitoreo de sensores en edificios. Los sensores (o el simulador) envían lecturas por MQTT,
el backend las guarda y genera alertas, y el panel web permite administrar edificios, zonas y nodos,
y atender alertas.

## Componentes

| Componente | Dónde corre | Puerto en tu equipo | Qué hace |
|---|---|---|---|
| PostgreSQL (`success_db`) | Docker | `127.0.0.1:5432` | Base de datos `success` |
| Mosquitto (`sentinel-mosquitto`) | Docker | `8883` (MQTT sobre TLS) | Broker MQTT. No acepta conexiones anónimas ni sin TLS |
| monolito-escucha (`monolito_escucha`) | Docker | `8089` | Recibe telemetría, guarda lecturas y genera alertas. Aplica las migraciones de la base |
| monolito-consulta (`monolito_consulta`) | Docker | `8090` | API del panel: edificios, zonas, nodos, alertas. Exige sesión de Firebase |
| bridge (`sentinel-bridge`) | Docker | `8766` | Recibe datos del simulador y los reenvía a escucha |
| simulador (`sentinel-mqtt-simulator`) | Docker | interno | Genera lecturas de sensores de prueba |
| Frontend | Tu equipo (Vite) | `5173` por defecto | Panel web de administración |

El mock backend ya no forma parte del sistema.

---

## Primera ejecución, paso a paso

### 0. Requisitos

- Docker y Docker Compose v2
- Node.js (una versión LTS reciente) y npm, para el frontend
- `openssl` para generar contraseñas
- Un proyecto de Firebase con **Authentication → Google** activado y tu correo de administrador

### 1. Crear el `.env` de la raíz

Este archivo lo lee `docker compose`. No se sube a git.

```bash
cp .env.example .env
```

Completa estas variables:

| Variable | Valor |
|---|---|
| `POSTGRES_DB` | `success` (o el nombre que quieras) |
| `POSTGRES_USER` | `admin` (o el que quieras) |
| `POSTGRES_PASSWORD` | una contraseña generada, ver abajo |
| `MQTT_ADMIN_PASSWORD` | una contraseña generada, ver abajo |
| `MQTT_CONSUMER_USERNAME` | `escucha-consumer` |
| `MQTT_CONSUMER_PASSWORD` | una contraseña generada, ver abajo |
| `SENTINEL_NODE_TOKENS` | déjala vacía en la primera ejecución |
| `FIREBASE_PROJECT_ID` | el ID del proyecto de Firebase (Configuración del proyecto → General) |
| `FIREBASE_ADMIN_EMAILS` | tu correo, con el que vas a iniciar sesión |

Para generar cada contraseña:

```bash
openssl rand -hex 32
```

Usa una contraseña distinta para cada variable y guárdalas en un gestor de contraseñas.

> `docker compose` solo toma las variables de Firebase del `.env` de la **raíz**. El archivo
> `backend/monolito-consulta/.env` solo se usa si ejecutas el backend fuera de Docker.

### 2. Levantar la infraestructura

```bash
./bootstrap.sh
```

El script hace lo siguiente, en orden. Puedes volver a ejecutarlo sin problema:

1. Genera los certificados TLS del broker en `backend/mosquitto/certs/`, si no existen.
2. Crea la base de seguridad del broker en `backend/mosquitto/data/`, si no existe. Esa base guarda
   las cuentas MQTT, así que **no la borres** si ya tiene nodos registrados.
3. Levanta Mosquitto.
4. Crea o actualiza la cuenta `escucha-consumer` con `MQTT_CONSUMER_PASSWORD`.
5. Levanta el resto del backend con `docker compose up -d --build`: PostgreSQL, escucha, consulta,
   bridge y simulador.

Si el script se detiene, corrige el error que muestra y vuelve a ejecutarlo.

### 3. Verificar

```bash
docker compose ps
```

Deben aparecer `success_db` y `sentinel-mosquitto` como `healthy`, y `monolito_escucha`, `monolito_consulta`,
`sentinel-bridge` y `sentinel-mqtt-simulator` como `Up`.

```bash
curl http://localhost:8089/health    # escucha
curl http://localhost:8090/health    # consulta
curl -i http://localhost:8090/nodes  # debe responder 401: la ruta exige sesión
```

Si `/nodes` responde `503`, `FIREBASE_PROJECT_ID` está vacío en el `.env` de la raíz.

### 4. Frontend

```bash
cd frontend
cp .env.example .env
```

En `frontend/.env` completa los valores `VITE_FIREBASE_*` con la configuración del SDK de tu app web
(Firebase console → Configuración del proyecto → Tus apps). `VITE_API_URL` ya apunta a `http://localhost:8090`.

```bash
npm install
npm run dev
```

Abre `http://localhost:5173`, pulsa **Iniciar sesión** e inicia sesión con Google usando el correo de
`FIREBASE_ADMIN_EMAILS`. Si la cuenta no está en esa lista, el panel mostrará que no tiene permisos.

### 5. Ver el flujo de datos

```bash
docker compose logs -f mqtt-sensor-simulator   # lecturas generadas
docker compose logs -f monolito-escucha        # lecturas guardadas y alertas
```

---

## Comandos del día a día

```bash
docker compose ps                    # estado de los servicios
docker compose logs -f <servicio>    # logs, por ejemplo monolito-escucha
docker compose restart <servicio>    # reiniciar un servicio
docker compose stop                  # detener, conserva los datos
docker compose up -d --build         # reconstruir imágenes y levantar
./bootstrap.sh                       # volver a preparar broker y cuenta de escucha
```

> `docker compose down -v` **borra la base de datos** y los volúmenes del simulador. Úsalo solo si
> quieres empezar de cero.

## Estructura del repositorio

```
sentinel-builder/
├── compose.yaml          # servicios Docker
├── bootstrap.sh          # preparación del broker y arranque del backend
├── .env                  # variables de Docker Compose (no se sube a git)
├── backend/
│   ├── monolito-escucha/ # ingesta de telemetría y alertas
│   ├── monolito-consulta/# API del panel
│   └── mosquitto/        # configuración, certificados y base del broker
├── simulator/            # simulador de sensores y bridge
└── frontend/             # panel web (React + Vite)
```

## Solución de problemas

| Síntoma | Causa probable |
|---|---|
| `required variable MQTT_ADMIN_PASSWORD is missing` | Falta la variable en el `.env` de la raíz |
| `No module named 'app.scripts'` | Imagen de consulta antigua. Usa `docker compose run --build` o `./bootstrap.sh` |
| `/nodes` responde `503` | `FIREBASE_PROJECT_ID` vacío |
| Inicias sesión y el panel dice que no tienes permisos | Tu correo no está en `FIREBASE_ADMIN_EMAILS` |
| El frontend dice que faltan variables de Firebase | Falta completar `frontend/.env` |
| El simulador no conecta con el broker | Certificados o base del broker incompletos. Revisa `backend/mosquitto/README.md` |

---

*Última actualización: 2026-11-16*

# Sentinel Building - Sistema Integrado

Sistema completo de monitoreo de sensores en edificios con arquitectura distribuida basada en contenedores Docker.

## 📋 Descripción General

Sentinel Building es un sistema de ingesta y gestión de lecturas de sensores distribuidos en edificios. Incluye:
- **Backend API** - FastAPI para gestión de datos
- **Simulador MQTT** - Generador de datos de sensores virtuales
- **Bridge** - Receptor de datos del simulador
- **Broker MQTT** - Mosquitto para pub/sub de telemetría
- **Base de datos** - PostgreSQL para persistencia

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    SENTINEL BUILDING                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ MQTT Simulator   │──│   Mosquitto      │                │
│  │ (Sensores)       │  │   (Broker MQTT)  │                │
│  └────────┬─────────┘  └──────────────────┘                │
│           │                    ▲                            │
│           │                    │ sentinel/v1/SB-001/*       │
│           ▼                    │                            │
│  ┌──────────────────┐  ┌──────┴──────────┐                │
│  │  Bridge Service  │──│  Mock Backend   │                │
│  │  (HTTP receiver) │  │  (FastAPI)      │                │
│  └────────┬─────────┘  └─────────────────┘                │
│           │                                                │
│           ▼                                                │
│  ┌─────────────────────────────────────────┐              │
│  │   MONOLITO-ESCUCHA (FastAPI Backend)    │              │
│  │   - Gestión de sensores                 │              │
│  │   - Procesamiento de lecturas            │              │
│  │   - Alertas                              │              │
│  └────────────┬────────────────────────────┘              │
│               │                                            │
│               ▼                                            │
│  ┌─────────────────────────────────────────┐              │
│  │      PostgreSQL (Base de Datos)         │              │
│  │      - Buildings, Zones, Nodes          │              │
│  │      - Sensors, Readings, Alerts        │              │
│  └─────────────────────────────────────────┘              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Inicio Rápido

### Prerequisitos
- Docker
- Docker Compose
- Git

### Levantar los Servicios

```bash
cd /home/santiago/Documentos/sentinel-builder
docker compose up -d
```

El sistema estará completamente operativo en ~15 segundos.

### Verificar Estado

```bash
docker compose ps
```

Resultado esperado:
```
NAME                      STATUS              PORTS
monolito_escucha          Up                  0.0.0.0:8089->8089/tcp
sentinel-bridge           Up                  0.0.0.0:8766->8766/tcp
sentinel-mock-backend     Up                  0.0.0.0:8000->8000/tcp
sentinel-mosquitto        Up (healthy)        0.0.0.0:1883->1883/tcp
sentinel-mqtt-simulator   Running             (internal)
success_db                Up (healthy)        127.0.0.1:5432->5432/tcp
```

## 📡 Servicios Disponibles

### 1. Backend API (Monolito-Escucha)
- **Puerto:** 8089
- **URL:** `http://localhost:8089`
- **Documentación:** `http://localhost:8089/docs`
- **Health:** `http://localhost:8089/health`

**Tecnología:** FastAPI + SQLAlchemy + PostgreSQL

### 2. Broker MQTT (Mosquitto)
- **Puerto:** 1883 (MQTT)
- **Puerto:** 9001 (WebSocket)
- **Host:** `mosquitto` (dentro de Docker)
- **Anónimo:** Habilitado

**Canales de Telemetría:**
- `sentinel/v1/SB-001/telemetry/batch` - Lotes de telemetría
- `sentinel/v1/SB-001/telemetry/aggregate` - Agregados
- `sentinel/v1/SB-001/emergency` - Alertas de emergencia

### 3. Mock Backend (FastAPI)
- **Puerto:** 8000
- **URL:** `http://localhost:8000`
- **Health:** `http://localhost:8000/health`

**Propósito:** Simular backend remoto para pruebas

### 4. Bridge Service
- **Puerto:** 8766
- **URL:** `http://localhost:8766`

**Propósito:** Recibir datos del simulador y procesarlos

### 5. Base de Datos PostgreSQL
- **Puerto:** 5432 (solo localhost)
- **Host:** `localhost`
- **Usuario:** admin
- **Contraseña:** change_me (en `.env`)
- **BD:** success

### 6. Simulador MQTT
- **Tipo:** Generador de datos de sensores
- **Estado:** REPL interactiva
- **Canales:** Publica en Mosquitto

## 📊 Endpoints de API

### Telemetría

#### POST - Crear Telemetría
```
POST http://localhost:8089/telemetry/aggregate
Content-Type: application/json

{
  "schema_version": "1.0",
  "message_uid": "msg-uuid-123",
  "message_type": "telemetry",
  "building_uid": "bld-123",
  "building_code": "BLDG-001",
  "generated_at": "2026-10-27T22:30:00Z",
  "sent_at": "2026-10-27T22:30:01Z",
  "sequence_number": 1,
  "priority": "normal",
  "quality": "valid",
  "delivery_policy": "immediate",
  "delivery_status": "pending",
  "transport": "http",
  "window": {
    "start": "2026-10-27T22:20:00Z",
    "end": "2026-10-27T22:30:00Z",
    "duration_seconds": 600,
    "sample_count": 10
  },
  "bridges": [
    {
      "node_uid": "node-123",
      "node_code": "NODE-001",
      "node_name": "Node 1",
      "floor": 1,
      "zone_uid": "zone-123",
      "zone_code": "ZONE-A",
      "sensors": [
        {
          "sensor_uid": "sensor-123",
          "sensor_code": "SENSOR-001",
          "sensor_model": "TMP36",
          "measurement_type": "temperature",
          "sample_count": 10,
          "data": {
            "average_avg_c": 24.5,
            "maximum_avg_c": 25.0,
            "maximum_c": 26.5
          }
        }
      ]
    }
  ]
}
```

**Response (202 Accepted):**
```json
{
  "message_uid": "msg-uuid-123",
  "readings_created": 1,
  "errors": []
}
```

#### GET - Obtener Telemetría por Node (Paginado)
```
GET http://localhost:8089/telemetry/node/{node_id}?limit=100&offset=0
```

**Parámetros:**
- `node_id` (path): ID del nodo
- `limit` (query): Registros por página (1-1000, default: 100)
- `offset` (query): Desplazamiento (default: 0)

**Response (200):**
```json
{
  "node": {
    "node_id": 1,
    "code": "NODE-001",
    "name": "Node Principal",
    "ip_address": "192.168.1.100",
    "local_storage_mb": 512.50,
    "registered_at": "2026-10-27T10:00:00Z",
    "last_signal_received_at": "2026-10-27T22:30:00Z"
  },
  "zone": {
    "zone_id": 1,
    "code": "ZONA-A",
    "floor": 1
  },
  "building": {
    "building_id": 1,
    "name": "Edificio Principal",
    "address": "Calle Principal 123"
  },
  "pagination": {
    "limit": 100,
    "offset": 0,
    "count": 2
  },
  "telemetry_readings": [
    {
      "reading": {
        "reading_id": 101,
        "sensor_id": 1,
        "receiving_node_id": 1,
        "measured_at": "2026-10-27T22:30:00Z",
        "received_at": "2026-10-27T22:30:01Z",
        "measured_value": "24.50",
        "sequence_number": 10
      },
      "sensor": {
        "sensor_id": 1,
        "code": "SENSOR-001",
        "connection_type": "I2C",
        "connection_address": "0x77",
        "sensor_type": {
          "sensor_type_id": 1,
          "name": "Temperature Sensor",
          "sampling_interval": 30,
          "default_unit": "Celsius",
          "normal_minimum": 15.0,
          "normal_maximum": 30.0
        },
        "primary_node": {
          "node_id": 1,
          "code": "NODE-001",
          "name": "Node Principal"
        }
      }
    }
  ]
}
```

### Otros Endpoints

**Documentación completa:** `http://localhost:8089/docs`

## 🔌 Monitoreo MQTT

### Suscribirse a Canales

```bash
# Ver todos los mensajes de telemetría
docker exec sentinel-mosquitto mosquitto_sub -h 127.0.0.1 -t "sentinel/v1/SB-001/#" -v

# Solo telemetría batch
docker exec sentinel-mosquitto mosquitto_sub -h 127.0.0.1 -t "sentinel/v1/SB-001/telemetry/batch" -v

# Solo emergencias
docker exec sentinel-mosquitto mosquitto_sub -h 127.0.0.1 -t "sentinel/v1/SB-001/emergency" -v
```

### Publicar Mensaje de Prueba

```bash
docker exec sentinel-mosquitto mosquitto_pub -h 127.0.0.1 -t "test/topic" -m "Hello Sentinel"
```

## 🎮 Interactuar con el Simulador

El simulador está en modo REPL interactivo. Accede con:

```bash
docker attach sentinel-mqtt-simulator
```

**Comandos disponibles:**
```
bridge1 on|off        - Activar/desactivar bridge 1
bridge2 on|off        - Activar/desactivar bridge 2
lora1 on|off          - Activar/desactivar LoRa 1
lora2 on|off          - Activar/desactivar LoRa 2
mesh on|off           - Activar/desactivar mesh
mqtt on|off           - Activar/desactivar MQTT
anomaly               - Inyectar anomalía
clear                 - Limpiar anomalías
status                - Ver estado actual
quit                  - Salir
```

**Ejemplo:**
```
mqtt-sim> mqtt on
Publicación MQTT activada
mqtt-sim> status
Bridge 1: UP, Bridge 2: DOWN, LoRa 1: UP, LoRa 2: DOWN
MQTT: ON, Mesh: UP
```

## 🔧 Variables de Entorno

Archivo `.env` en la raíz:

```env
POSTGRES_DB=success
POSTGRES_USER=admin
POSTGRES_PASSWORD=change_me
```

## 📁 Estructura de Directorios

```
sentinel-builder/
├── compose.yaml              # Orquestación de servicios
├── mosquitto.conf            # Configuración de Mosquitto
├── .env                       # Variables de entorno
├── README.md                  # Este archivo
├── backend/
│   ├── monolito-escucha/     # Backend principal
│   ├── sumothings_db/        # Migraciones BD
│   └── .env                  # Variables del backend
├── simulator/
│   ├── Dockerfile            # Imagen del simulador
│   ├── mqtt_sensor_simulator.py    # Simulador MQTT
│   ├── bridge/bridge_service.py    # Servicio bridge
│   ├── mock_backend/         # Mock backend
│   └── requirements.txt       # Dependencias Python
└── frontend/
    └── (estructura pendiente)
```

## 🐳 Comandos Útiles

### Ver Logs

```bash
# Todos los servicios
docker compose logs -f

# Solo backend
docker compose logs -f monolito-escucha

# Solo simulador
docker compose logs -f mqtt-sensor-simulator

# Solo MQTT broker
docker compose logs -f mosquitto
```

### Detener/Reiniciar

```bash
# Detener todo (mantiene volúmenes)
docker compose stop

# Detener todo (elimina volúmenes)
docker compose down -v

# Reiniciar un servicio
docker compose restart monolito-escucha

# Reconstruir imágenes
docker compose up -d --build
```

### Acceder a Contenedores

```bash
# Terminal en backend
docker exec -it monolito_escucha bash

# Terminal en simulador
docker exec -it sentinel-mqtt-simulator bash

# Terminal en Mosquitto
docker exec -it sentinel-mosquitto sh
```

## 🐘 Acceso a Base de Datos

### Con psql

```bash
psql -h 127.0.0.1 -U admin -d success -W
# Password: change_me
```

### Ver lecturas recientes

```sql
SELECT r.reading_id, s.code as sensor_code, r.measured_value, r.received_at
FROM reading r
JOIN sensor s ON r.sensor_id = s.sensor_id
ORDER BY r.received_at DESC
LIMIT 10;
```

## ⚠️ Troubleshooting

### "Connection refused" en Mosquitto
**Problema:** El simulador no puede conectarse a Mosquitto
**Solución:** 
- Verificar que Mosquitto esté levantado: `docker compose ps`
- Revisar archivo `mosquitto.conf` esté en la raíz
- Reiniciar contenedor: `docker compose restart mosquitto`


**Última actualización:** 2026-10-27
**Versión:** 0.1.0

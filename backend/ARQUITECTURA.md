# Arquitectura de Microservicios - Sentinel Builder

Documento que describe la arquitectura y responsabilidades de los microservicios en el backend de Sentinel Builder.

---

## 📋 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Monolito Escucha](#monolito-escucha)
3. [Monolito Consulta](#monolito-consulta)
4. [Comunicación entre Servicios](#comunicación-entre-servicios)
5. [Base de Datos](#base-de-datos)
6. [MQTT Broker](#mqtt-broker)
7. [Despliegue](#despliegue)

---

## Visión General

La arquitectura está compuesta por dos microservicios que trabajan de forma complementaria:

```
┌─────────────────────────────────────────────┐
│            Bridges/Sensores                 │
│        (Enviando datos por MQTT)            │
└────────────────┬────────────────────────────┘
                 │
        ┌────────▼────────┐
        │  MQTT Broker    │
        │  (mosquitto)    │
        └────────┬────────┘
                 │
        ┌────────▼────────────────┐
        │  Monolito Escucha       │
        │  (MQTT Listener)        │
        │  - MQTT Consumer        │
        │  - Telemetría POST      │
        │  - Guarda Readings      │
        └────────┬────────────────┘
                 │
        ┌────────▼──────────────┐
        │  PostgreSQL Database  │
        │  (Compartida)         │
        └────────▲──────────────┘
                 │
        ┌────────┴──────────────┐
        │  Monolito Consulta    │
        │  (CRUD Manager)       │
        │  - Buildings CRUD     │
        │  - Zones CRUD         │
        │  - Nodes CRUD         │
        │  - Sensors CRUD       │
        │  - Readings GET       │
        │  - Alerts CRUD        │
        │  - Users/Roles CRUD   │
        └───────────────────────┘
             ↓              ↓
         Clientes      Reportes
```

---

## Monolito Escucha

### 🎯 Propósito
Escuchar continuamente el broker MQTT y procesar telemetría en tiempo real.

### 📍 Ubicación
```
/home/santiago/Documentos/sentinel-builder/backend/monolito-escucha/
```

### 🚀 Responsabilidades

#### 1. **MQTT Consumer** (Siempre Activo)
- Escucha el broker MQTT (host: `mosquitto`, port: `1883`)
- Procesa mensajes de telemetría en tiempo real
- Maneja reconexiones automáticas
- Log de errores y desconexiones
- Se inicia automáticamente al arrancar la app

#### 2. **Procesamiento de Telemetría**
- Endpoint: `POST /telemetry/aggregate` (Status: 202 Accepted)
- Recibe datos agregados de bridges
- Valida estructura de datos
- Crea automáticamente readings
- Guarda en PostgreSQL

**Validaciones:**
```
✅ Building existe
✅ Zone existe
✅ Node existe
✅ Sensor existe
✅ Sensor type válido
✅ Timestamp es válido
```

#### 3. **Almacenamiento de Readings**
- Tabla: `readings`
- Automático desde MQTT o POST /telemetry/aggregate
- Incluye timestamp, valor, secuencia
- No hay endpoints para crear/actualizar (solo POST telemetry)

### 📡 Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Info de la API |
| GET | `/health` | Health check |
| POST | `/telemetry/aggregate` | Procesa telemetría |

**Total**: 3 endpoints

### 🔧 Configuración

**Variables de entorno:**
```env
DATABASE_URL=postgresql+asyncpg://sentinel:sentinel123@db:5432/sentinel_db
APP_ENV=production
```

**MQTT:**
- Host: `mosquitto`
- Puerto: `1883`
- Protocolo: MQTT v3.1.1
- Tópicos: Configurables en `mqtt_handler.py`

### 📊 Estado de la Aplicación

```
✅ MQTT Consumer (siempre escuchando)
✅ Procesamiento de Telemetría
✅ Almacenamiento de Readings
✅ Validaciones de datos
✅ Logs automáticos
```

---

## Monolito Consulta

### 🎯 Propósito
Gestionar la infraestructura y datos del sistema mediante CRUD.

### 📍 Ubicación
```
/home/santiago/Documentos/sentinel-builder/backend/monolito-consulta/
```

### 🚀 Responsabilidades

#### 1. **CRUD Infraestructura**
- Edificios (Buildings): Create, Read, Update, Delete ✅
- Zonas (Zones): CRUD completo ✅
- Nodos (Nodes): CRUD + búsqueda por código ✅
- Sensores: CRUD + búsqueda por código ✅
- Tipos de Sensor: CRUD ✅

#### 2. **Lectura de Datos**
- Readings: Solo GET (lectura)
- Alertas: CRUD (puede actualizar estado)
- Registros de Conectividad: CRUD
- Logs: GET only

#### 3. **Gestión de Acceso**
- Usuarios (AppUsers): CRUD
- Roles (AppRoles): CRUD
- Asociación usuario-rol

### 📡 Endpoints

| Recurso | POST | GET | PATCH | DELETE |
|---------|------|-----|-------|--------|
| Buildings | ✅ | ✅ | ✅ | ✅ |
| Zones | ✅ | ✅ | ✅ | ✅ |
| Nodes | ✅ | ✅ | ✅ | ✅ |
| Sensors | ✅ | ✅ | ✅ | ✅ |
| SensorTypes | ✅ | ✅ | ✅ | ✅ |
| Readings | ❌ | ✅ | ❌ | ❌ |
| Alerts | ✅ | ✅ | ✅ | ❌ |
| ConnectivityLogs | ✅ | ✅ | ✅ | ❌ |
| Users | ✅ | ✅ | ✅ | ✅ |
| Roles | ✅ | ✅ | ✅ | ✅ |

**Total**: 60+ endpoints

### 🔧 Configuración

**Variables de entorno:**
```env
DATABASE_URL=postgresql+asyncpg://sentinel:sentinel123@db:5432/sentinel_db
APP_ENV=production
```

---

## Comunicación entre Servicios

### BD Compartida
Ambos servicios comparten una base de datos PostgreSQL:

```
Monolito Escucha ──┐
                   ├──> PostgreSQL (sentinel_db)
Monolito Consulta ─┘
```

**Beneficios:**
- Consistencia de datos
- Transacciones atómicas
- Relaciones referenciadas
- Una sola fuente de verdad

**Modelos Compartidos:**
- Building
- Zone
- Node
- Sensor
- SensorType
- Reading ⬅️ Escrita por Escucha, leída por Consulta
- Alert
- ConnectivityLog
- AppUser
- AppRole

### Flujo de Datos

```
1️⃣ Bridge envía MQTT
   ↓
2️⃣ Monolito Escucha recibe
   ├─ MQTT Consumer (escucha)
   ├─ TelemetryService (procesa)
   └─ ReadingRepository (guarda)
   ↓
3️⃣ PostgreSQL Database
   ├─ readings (insertado por Escucha)
   ├─ Buildings (consultado/escrito por Consulta)
   ├─ Zones (consultado/escrito por Consulta)
   ├─ Nodes (consultado/escrito por Consulta)
   ├─ Sensors (consultado/escrito por Consulta)
   └─ alerts (consultado/escrito por Consulta)
   ↓
4️⃣ Cliente consulta datos
   ↓
5️⃣ Monolito Consulta
   └─ Retorna información
```

---

## Base de Datos

### PostgreSQL

**Configuración:**
```yaml
Host: db (en Docker) / localhost
Port: 5432
Database: sentinel_db
User: sentinel
Password: sentinel123
```

**Tablas Principales:**

| Tabla | Escritura | Lectura |
|-------|-----------|---------|
| buildings | Consulta | Ambos |
| zones | Consulta | Ambos |
| nodes | Consulta | Ambos |
| sensors | Consulta | Ambos |
| sensor_types | Consulta | Ambos |
| readings | **Escucha** | Ambos |
| alerts | Consulta | Ambos |
| connectivity_logs | Escucha | Ambos |
| app_users | Consulta | Ambos |
| app_roles | Consulta | Ambos |

### Migraciones

**Monolito Escucha:**
```bash
cd monolito-escucha
alembic upgrade head
```

**Monolito Consulta:**
```bash
cd monolito-consulta
alembic upgrade head
```

---

## MQTT Broker

### Mosquitto

**Configuración por defecto:**
```
Host: mosquitto (en Docker)
Port: 1883
Protocol: MQTT v3.1.1
```

**Tópicos:**
Configurable según los sensores y bridges en `app/core/mqtt_handler.py`

**Formato de mensaje esperado:**
```json
{
  "building": {
    "building_id": 1,
    "name": "Edificio SB-001"
  },
  "bridges": [
    {
      "code": "NODE-FLOOR-1",
      "ip_address": "192.168.1.10"
    }
  ],
  "sensors": [
    {
      "code": "SENSOR-1",
      "type": "ADXL355"
    }
  ],
  "data": [
    {
      "sensor_code": "SENSOR-1",
      "value": 0.5,
      "timestamp": "2026-10-20T18:00:00Z"
    }
  ]
}
```

---

## Despliegue

### Docker Compose

```bash
# Monolito Escucha
cd monolito-escucha
docker-compose up -d

# Monolito Consulta (en otro terminal)
cd monolito-consulta
docker-compose up -d
```

**Servicios levantados:**
- PostgreSQL (5432)
- Mosquitto (1883)
- Monolito Escucha (8000)
- Monolito Consulta (8001)

### Verificación

```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:8001/health

# Documentación
open http://localhost:8000/docs
open http://localhost:8001/docs
```

---

## Rutas de Acceso

### Monolito Escucha

| Servicio | Puerto | Ruta |
|----------|--------|------|
| API | 8000 | http://localhost:8000 |
| Swagger | 8000 | http://localhost:8000/docs |
| ReDoc | 8000 | http://localhost:8000/redoc |

### Monolito Consulta

| Servicio | Puerto | Ruta |
|----------|--------|------|
| API | 8001 | http://localhost:8001 |
| Swagger | 8001 | http://localhost:8001/docs |
| ReDoc | 8001 | http://localhost:8001/redoc |

### MQTT

| Servicio | Puerto | URL |
|----------|--------|-----|
| Mosquitto | 1883 | mqtt://localhost:1883 |

### PostgreSQL

| Servicio | Puerto | Host |
|----------|--------|------|
| Database | 5432 | localhost:5432 |

---

## Flujos Típicos de Uso

### 1. Setup Inicial (Monolito Consulta)

```
POST /buildings          (crear edificio)
POST /zones              (crear zona)
POST /nodes              (crear bridge/nodo)
POST /sensor-types       (crear tipos)
POST /sensors            (crear sensores)
```

### 2. Ingesta de Datos (Monolito Escucha)

```
Bridge conectado a MQTT
  ↓
Envía telemetría
  ↓
Monolito Escucha recibe
  ↓
MQTT Consumer procesa
  ↓
TelemetryService valida
  ↓
ReadingRepository guarda
  ↓
PostgreSQL persiste
```

### 3. Consulta de Datos (Monolito Consulta)

```
GET /readings/sensor/{id}         (readings por sensor)
GET /readings/receiving-node/{id} (readings por nodo)
GET /alerts/unhandled             (alertas sin procesar)
PATCH /alerts/{id}                (marcar como procesada)
```

---

## Recomendaciones

### ✅ Mejor Práctica
- **Monolito Escucha**: Dejar siempre corriendo para ingesta
- **Monolito Consulta**: Dejar siempre corriendo para gestión
- Mantener MQTT Consumer activo
- Usar timestamps UTC (formato ISO 8601 con Z)
- Validar códigos de recursos únicos

### ⚠️ Evitar
- Escribir directamente en BD sin usar APIs
- Cambiar esquema sin migración Alembic
- Usar contraseñas en código (usar `.env`)
- Desactivar MQTT Consumer
- Timestamps sin zona horaria

### 🔐 Seguridad
- Cambiar credenciales por defecto
- Usar MQTT con autenticación en producción
- Implementar JWT en endpoints
- Logs de auditoría para operaciones críticas
- Usar HTTPS en producción

---

## Próximos Pasos

### 🚀 Planned Features
- [ ] Autenticación JWT
- [ ] Rate limiting
- [ ] Compresión de lecturas históricas
- [ ] Caché de consultas frecuentes
- [ ] Métricas Prometheus
- [ ] Health checks avanzados

### 🔄 Mejoras Futuras
- Separar lectura/escritura en replicas
- Implementar event sourcing para auditoría
- Agregar API Gateway
- Implementar GraphQL
- Monitoreo con ELK Stack

---

**Última actualización**: 2026-10-30  
**Versión**: 1.0  
**Estado**: Producción  
**Separación clara**: ✅ Escucha (MQTT) + Consulta (CRUD)

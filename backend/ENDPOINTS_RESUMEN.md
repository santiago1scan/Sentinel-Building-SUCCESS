# Endpoints Resumen - Sentinel Builder Backend

**Última actualización**: 2026-10-30

---

## 🎯 Monolito Escucha (Principal)

**Puerto**: 8000  
**Base URL**: `http://localhost:8000`  
**Status**: ✅ Activo con MQTT

### MQTT & Telemetría
```
POST   /telemetry/aggregate          # Procesa telemetría
GET    /telemetry/node/{node_id}     # Telemetría por nodo
```

### Infraestructura
```
# Buildings
POST   /buildings
GET    /buildings
GET    /buildings/{building_id}
PATCH  /buildings/{building_id}
DELETE /buildings/{building_id}
GET    /buildings/{building_id}/zones

# Zones
POST   /zones
GET    /zones
GET    /zones/{zone_id}
PATCH  /zones/{zone_id}
DELETE /zones/{zone_id}
GET    /zones/building/{building_id}

# Nodes
POST   /nodes
GET    /nodes
GET    /nodes/{node_id}
GET    /nodes/code/{code}
PATCH  /nodes/{node_id}
DELETE /nodes/{node_id}
GET    /nodes/zone/{zone_id}
GET    /nodes/{node_id}/sensors
GET    /nodes/{node_id}/connectivity-logs
GET    /nodes/{node_id}/received-readings
```

### Sensores
```
# Sensor Types
POST   /sensor-types
GET    /sensor-types
GET    /sensor-types/{sensor_type_id}
PATCH  /sensor-types/{sensor_type_id}
DELETE /sensor-types/{sensor_type_id}

# Sensors
POST   /sensors
GET    /sensors
GET    /sensors/{sensor_id}
GET    /sensors/code/{code}
PATCH  /sensors/{sensor_id}
DELETE /sensors/{sensor_id}
GET    /sensors/{sensor_id}/readings
```

### Datos
```
# Readings (Lecturas)
POST   /readings
GET    /readings
GET    /readings/{reading_id}
GET    /readings/sensor/{sensor_id}
GET    /readings/receiving-node/{receiving_node_id}

# Alerts (Alertas)
POST   /alerts
GET    /alerts
GET    /alerts/{alert_id}
GET    /alerts/event-uuid/{event_uuid}
PATCH  /alerts/{alert_id}
GET    /alerts/unhandled

# Connectivity Logs
POST   /connectivity-logs
GET    /connectivity-logs
GET    /connectivity-logs/{connectivity_id}
GET    /connectivity-logs/node/{node_id}/active
```

### Gestión
```
# App Users
POST   /app-users
GET    /app-users
GET    /app-users/{user_id}
GET    /app-users/email/{email}
PATCH  /app-users/{user_id}
DELETE /app-users/{user_id}

# App Roles
POST   /app-roles
GET    /app-roles
GET    /app-roles/{role_code}
PATCH  /app-roles/{role_code}
DELETE /app-roles/{role_code}
```

### General
```
GET    /                             # Info
GET    /health                       # Health check
GET    /docs                         # Swagger UI
GET    /redoc                        # ReDoc
```

---

## 📚 Monolito Consulta (Legado)

**Puerto**: 8001  
**Base URL**: `http://localhost:8001`  
**Status**: ⏳ Disponible pero sin MQTT

### General
```
GET    /                             # Info
GET    /health                       # Health check
GET    /docs                         # Swagger UI
```

---

## 📊 Query Parameters Comunes

Todos los endpoints `GET` de listado soportan:
```
?limit=100    # Registros por página (1-1000, default: 100)
?offset=0     # Desplazamiento (default: 0)
```

Ejemplo:
```
GET /readings?limit=50&offset=100
```

---

## 📋 Códigos de Respuesta

| Código | Significado |
|--------|-------------|
| 200 | OK - Exitoso |
| 201 | Created - Creado |
| 202 | Accepted - Aceptado (procesamiento asincrónico) |
| 204 | No Content - Exitoso sin respuesta |
| 400 | Bad Request - Solicitud inválida |
| 404 | Not Found - Recurso no encontrado |
| 409 | Conflict - Duplicado o FK violation |
| 422 | Unprocessable Entity - Error de validación |
| 503 | Service Unavailable - BD no disponible |

---

## 🔑 Ejemplos rápidos

### Crear edificio
```bash
curl -X POST http://localhost:8000/buildings \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Edificio SB-001",
    "address": "Bogotá, Colombia"
  }'
```

### Listar nodos
```bash
curl http://localhost:8000/nodes?limit=20
```

### Obtener nodo por código
```bash
curl http://localhost:8000/nodes/code/NODE-FLOOR-1
```

### Enviar telemetría
```bash
curl -X POST http://localhost:8000/telemetry/aggregate \
  -H "Content-Type: application/json" \
  -d '{
    "building": {...},
    "bridges": [...],
    "sensors": [...],
    "data": {...}
  }'
```

### Obtener lecturas de un sensor
```bash
curl http://localhost:8000/readings/sensor/1?limit=50
```

### Obtener alertas sin manejar
```bash
curl http://localhost:8000/alerts/unhandled
```

---

## 🔄 Flujos Comunes

### 1. Setup Inicial
```
1. POST /buildings              (crear edificio)
2. POST /zones                  (crear zona en edificio)
3. POST /nodes                  (crear nodo/bridge)
4. POST /sensor-types           (crear tipos de sensor)
5. POST /sensors                (crear sensores)
```

### 2. Recibir Datos
```
1. MQTT Broker recibe mensaje del bridge
2. MQTT Consumer procesa
3. POST /telemetry/aggregate procesa datos
4. Lecturas se guardan automáticamente
5. Alertas se generan si aplica
```

### 3. Consultar Datos
```
GET /readings/sensor/{id}       (lecturas por sensor)
GET /readings/receiving-node/{id}  (lecturas por nodo)
GET /alerts/unhandled           (alertas sin procesar)
PATCH /alerts/{id}              (marcar como procesada)
```

---

## 🔐 Headers Opcionales

```
X-Request-ID: custom-id         # ID de solicitud (se genera automáticamente)
Content-Type: application/json  # Para POST/PATCH
```

---

## 📈 Paginación

Todos los GET de listado retornan:
```json
[
  { "id": 1, "name": "...", ... },
  { "id": 2, "name": "...", ... }
]
```

Para la siguiente página:
```
GET /resource?limit=100&offset=100
```

---

## 🚀 Endpoint Favoritos

**Para desarrollo rápido:**
```bash
# Health check
curl http://localhost:8000/health

# Ver documentación interactiva
open http://localhost:8000/docs

# Listar todo
curl http://localhost:8000/buildings
curl http://localhost:8000/zones
curl http://localhost:8000/nodes
curl http://localhost:8000/sensors
curl http://localhost:8000/readings
curl http://localhost:8000/alerts
```

---

## 📞 Soporte

- **Documentación completa**: `monolito-escucha/ENDPOINTS.md`
- **Arquitectura**: `ARQUITECTURA.md`
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

**Estado**: ✅ Documentación actualizada  
**Versión**: 1.0  
**Última actualización**: 2026-10-30

# Monolito Consulta - Documentación de Endpoints

**Descripción**: Data Management & CRUD Operations  
**Base URL**: `http://localhost:8001`  
**Versión**: 0.1.0

---

## 🎯 Responsabilidad

Este monolito es responsable de:
- ✅ CRUD completo de Edificios (Buildings)
- ✅ CRUD completo de Zonas (Zones)
- ✅ CRUD completo de Nodos (Nodes)
- ✅ CRUD completo de Sensores (Sensors)
- ✅ CRUD completo de Tipos de Sensores
- ✅ Lectura de Readings (GET only)
- ✅ CRUD de Alertas (Create, Read, Update)
- ✅ Lectura de Registros de Conectividad
- ✅ CRUD de Usuarios (AppUsers)
- ✅ CRUD de Roles (AppRoles)

**NO tiene:**
- ❌ MQTT Consumer
- ❌ POST /telemetry/aggregate

---

## General

### GET `/`
Endpoint raíz con información de la API.

**Respuesta:**
```json
{
  "name": "Monolito Consulta",
  "description": "Data Management & CRUD Operations",
  "version": "0.1.0",
  "docs": "/docs",
  "health": "/health"
}
```

---

## Health & Status

### GET `/health`
Health check con verificación de conectividad a la base de datos.

**Respuesta:**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

---

## Tabla de Contenidos

1. [Edificios (Buildings)](#edificios-buildings)
2. [Zonas (Zones)](#zonas-zones)
3. [Nodos (Nodes)](#nodos-nodes)
4. [Tipos de Sensores](#tipos-de-sensores)
5. [Sensores](#sensores)
6. [Lecturas (Readings)](#lecturas-readings)
7. [Alertas](#alertas)
8. [Registros de Conectividad](#registros-de-conectividad)
9. [Usuarios de Aplicación](#usuarios-de-aplicación)
10. [Roles de Aplicación](#roles-de-aplicación)

---

## Edificios (Buildings)

### POST `/buildings`
Crear un nuevo edificio.

**Status**: 201 Created

**Request:**
```json
{
  "name": "Edificio SB-001",
  "address": "Bogotá, Colombia"
}
```

### GET `/buildings`
Listar todos los edificios.

**Query Parameters:**
- `limit`: int (1-1000, default: 100)
- `offset`: int (default: 0)

### GET `/buildings/{building_id}`
Obtener detalles de un edificio específico.

### PATCH `/buildings/{building_id}`
Actualizar información de un edificio.

### DELETE `/buildings/{building_id}`
Eliminar un edificio.

**Status**: 204 No Content

### GET `/buildings/{building_id}/zones`
Obtener todas las zonas de un edificio.

---

## Zonas (Zones)

### POST `/zones`
Crear una nueva zona.

**Status**: 201 Created

**Request:**
```json
{
  "building_id": 1,
  "name": "Zona Piso 1",
  "floor": 1
}
```

### GET `/zones`
Listar todas las zonas.

### GET `/zones/{zone_id}`
Obtener detalles de una zona específica.

### PATCH `/zones/{zone_id}`
Actualizar información de una zona.

### DELETE `/zones/{zone_id}`
Eliminar una zona.

### GET `/zones/building/{building_id}`
Obtener todas las zonas de un edificio.

---

## Nodos (Nodes)

### POST `/nodes`
Crear un nuevo nodo (bridge).

**Status**: 201 Created

**Request:**
```json
{
  "code": "NODE-FLOOR-1",
  "name": "Bridge 1 - Piso 1",
  "zone_id": 1,
  "ip_address": "192.168.1.10",
  "local_storage_mb": 1024,
  "last_signal_received_at": null
}
```

### GET `/nodes`
Listar todos los nodos.

### GET `/nodes/{node_id}`
Obtener detalles de un nodo específico.

### GET `/nodes/code/{code}`
Obtener un nodo por su código.

### PATCH `/nodes/{node_id}`
Actualizar información de un nodo.

### DELETE `/nodes/{node_id}`
Eliminar un nodo.

### GET `/nodes/zone/{zone_id}`
Obtener todos los nodos de una zona.

### GET `/nodes/{node_id}/sensors`
Obtener todos los sensores conectados a un nodo.

### GET `/nodes/{node_id}/connectivity-logs`
Obtener registros de conectividad de un nodo.

### GET `/nodes/{node_id}/received-readings`
Obtener todas las lecturas recibidas por un nodo.

---

## Tipos de Sensores

### POST `/sensor-types`
Crear un nuevo tipo de sensor.

**Request:**
```json
{
  "code": "ADXL355",
  "name": "Acelerómetro ADXL355",
  "unit": "m/s²",
  "description": "Sensor de aceleración"
}
```

### GET `/sensor-types`
Listar todos los tipos de sensores.

### GET `/sensor-types/{sensor_type_id}`
Obtener detalles de un tipo de sensor.

### PATCH `/sensor-types/{sensor_type_id}`
Actualizar información de un tipo de sensor.

### DELETE `/sensor-types/{sensor_type_id}`
Eliminar un tipo de sensor.

### GET `/sensor-types/{sensor_type_id}/sensors`
Obtener todos los sensores de un tipo específico.

---

## Sensores

### POST `/sensors`
Crear un nuevo sensor.

**Request:**
```json
{
  "code": "ADXL355-NODE-FLOOR-1",
  "primary_node_id": 1,
  "sensor_type_id": 1,
  "connection_type": "SPI",
  "connection_address": "0x1D"
}
```

### GET `/sensors`
Listar todos los sensores.

### GET `/sensors/{sensor_id}`
Obtener detalles de un sensor específico.

### GET `/sensors/code/{code}`
Obtener un sensor por su código.

### PATCH `/sensors/{sensor_id}`
Actualizar información de un sensor.

### DELETE `/sensors/{sensor_id}`
Eliminar un sensor.

### GET `/sensors/primary-node/{primary_node_id}`
Obtener todos los sensores de un nodo primario.

### GET `/sensors/sensor-type/{sensor_type_id}`
Obtener todos los sensores de un tipo específico.

### GET `/sensors/{sensor_id}/readings`
Obtener todas las lecturas de un sensor.

---

## Lecturas (Readings)

**Nota:** Las lecturas se crean automáticamente desde Monolito Escucha via MQTT

### GET `/readings`
Listar todas las lecturas.

**Query Parameters:**
- `limit`: int (1-1000, default: 100)
- `offset`: int (default: 0)

### GET `/readings/{reading_id}`
Obtener detalles de una lectura específica.

### GET `/readings/sensor/{sensor_id}`
Obtener todas las lecturas de un sensor (paginadas).

### GET `/readings/receiving-node/{receiving_node_id}`
Obtener todas las lecturas recibidas por un nodo (paginadas).

### GET `/readings/sequence/{sequence_number}`
Obtener lecturas por número de secuencia.

### GET `/readings/{reading_id}/alerts`
Obtener todas las alertas relacionadas con una lectura.

---

## Alertas

### POST `/alerts`
Crear una nueva alerta.

**Request:**
```json
{
  "event_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "reading_id": 1,
  "description": "Valor fuera de rango",
  "severity": "HIGH"
}
```

### GET `/alerts`
Listar todas las alertas.

### GET `/alerts/{alert_id}`
Obtener detalles de una alerta específica.

### GET `/alerts/event-uuid/{event_uuid}`
Obtener una alerta por su UUID de evento.

### PATCH `/alerts/{alert_id}`
Actualizar información de una alerta (marcar como manejada, etc).

### GET `/alerts/reading/{reading_id}`
Obtener todas las alertas relacionadas con una lectura.

### GET `/alerts/handled-by/{user_id}`
Obtener todas las alertas manejadas por un usuario.

### GET `/alerts/unhandled`
Obtener todas las alertas sin manejar.

---

## Registros de Conectividad

### POST `/connectivity-logs`
Crear un nuevo registro de conectividad.

**Request:**
```json
{
  "node_id": 1,
  "started_at": "2026-10-20T18:00:00Z",
  "ended_at": null
}
```

### GET `/connectivity-logs`
Listar todos los registros de conectividad.

### GET `/connectivity-logs/{connectivity_id}`
Obtener detalles de un registro de conectividad.

### PATCH `/connectivity-logs/{connectivity_id}`
Actualizar un registro de conectividad.

### GET `/connectivity-logs/node/{node_id}`
Obtener todos los registros de conectividad de un nodo.

### GET `/connectivity-logs/node/{node_id}/active`
Obtener todos los registros activos de conectividad de un nodo.

---

## Usuarios de Aplicación

### POST `/app-users`
Crear un nuevo usuario de aplicación.

**Request:**
```json
{
  "email": "user@example.com",
  "name": "Juan Pérez",
  "role_code": 1
}
```

### GET `/app-users`
Listar todos los usuarios de aplicación.

### GET `/app-users/{user_id}`
Obtener detalles de un usuario de aplicación.

### GET `/app-users/email/{email}`
Obtener un usuario por su email.

### PATCH `/app-users/{user_id}`
Actualizar información de un usuario.

### DELETE `/app-users/{user_id}`
Eliminar un usuario de aplicación.

### GET `/app-users/role/{role_code}`
Obtener todos los usuarios con un rol específico.

### GET `/app-users/{user_id}/handled-alerts`
Obtener todas las alertas manejadas por un usuario.

---

## Roles de Aplicación

### POST `/app-roles`
Crear un nuevo rol de aplicación.

**Request:**
```json
{
  "code": 1,
  "name": "Administrador",
  "description": "Acceso total al sistema"
}
```

### GET `/app-roles`
Listar todos los roles de aplicación.

### GET `/app-roles/{role_code}`
Obtener detalles de un rol por su código.

### GET `/app-roles/code/{role_code}`
Obtener un rol por su código (alias).

### PATCH `/app-roles/{role_code}`
Actualizar información de un rol.

### DELETE `/app-roles/{role_code}`
Eliminar un rol de aplicación.

### GET `/app-roles/{role_code}/users`
Obtener todos los usuarios con un rol específico.

---

## Códigos de Respuesta

| Código | Descripción |
|--------|-------------|
| 200 | OK - Exitoso |
| 201 | Created - Recurso creado |
| 204 | No Content - Exitoso sin contenido |
| 400 | Bad Request - Solicitud inválida |
| 404 | Not Found - Recurso no encontrado |
| 409 | Conflict - Duplicado o FK violation |
| 422 | Unprocessable Entity - Error de validación |
| 503 | Service Unavailable - BD no disponible |

---

## Documentación Interactiva

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

---

## Notas

- Todos los endpoints paginados usan `limit` y `offset`
- El límite por defecto es 100 registros con máximo 1000
- Los códigos de recurso se pueden usar para búsquedas alternativas
- Las lecturas se crean automáticamente desde Monolito Escucha
- La base de datos es compartida con Monolito Escucha

---

**Última actualización**: 2026-10-30  
**Versión**: 1.0  
**Estado**: ✅ CRUD Completo (sin MQTT)

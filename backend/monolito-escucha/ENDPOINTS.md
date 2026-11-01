# Monolito Escucha - Documentación de Endpoints

**Descripción**: MQTT Listener & Telemetry Processor  
**Base URL**: `http://localhost:8000`  
**Versión**: 0.1.0

---

## 🎯 Responsabilidad

Este monolito es responsable únicamente de:
- ✅ Escuchar el broker MQTT
- ✅ Procesar telemetría entrante
- ✅ Guardar lecturas en base de datos

---

## General

### GET `/`
Endpoint raíz con información de la API.

**Respuesta:**
```json
{
  "name": "Monolito Escucha",
  "description": "MQTT Listener & Telemetry Processor",
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

## MQTT & Telemetría

### POST `/telemetry/aggregate`
Procesa datos de telemetría agregada y guarda lecturas en la BD.

**Status**: 202 Accepted

**Descripción:**
- Recibe datos de bridges/sensores
- Valida estructura
- Crea readings automáticamente
- Guarda en PostgreSQL

**Request Body**: TelemetryAggregateDTO
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
      "type": "ADXL355",
      "node_id": 1
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

**Respuesta:**
```json
{
  "message_uid": "550e8400-e29b-41d4-a716-446655440000",
  "readings_created_count": 10,
  "errors": []
}
```

**Errores posibles:**
```json
{
  "status": 400,
  "error": "BadRequestError",
  "message": "Invalid telemetry data",
  "details": [...]
}
```

---

## Flujo de Datos

```
1. Bridge envía telemetría por MQTT
   └─> Tópicos configurables en mqtt_handler.py

2. MQTT Consumer recibe mensaje
   └─> Procesa automáticamente

3. TelemetryService procesa datos
   └─> Valida sensor codes
   └─> Valida nodos
   └─> Crea Reading objects

4. Readings se guardan en BD
   └─> Tabla: readings
   └─> Status: persistido

5. (Futuro) Alertas se generan si aplica
   └─> Tabla: alerts
```

---

## Configuración MQTT

**Broker default:**
```
Host: mosquitto
Port: 1883
Protocol: MQTT v3.1.1
```

**Tópicos:** Configurable en `app/core/mqtt_handler.py`

**Reconexión:** Automática en caso de desconexión

---

## Base de Datos

**Conexión:**
```
Host: db / localhost
Port: 5432
Database: sentinel_db
User: sentinel
```

**Tablas que escribe:**
- `readings` - Lecturas de sensores
- `connectivity_logs` - Logs de conectividad de nodos (automático)

**Tablas que consulta:**
- `buildings` - Para validar building_id
- `zones` - Para validar zone_id
- `nodes` - Para validar node_id
- `sensors` - Para validar sensor_id
- `sensor_types` - Para tipos de datos

---

## Códigos de Respuesta

| Código | Descripción |
|--------|-------------|
| 202 | Accepted - Telemetría aceptada para procesamiento |
| 400 | Bad Request - Datos inválidos |
| 404 | Not Found - Building/Zone/Node/Sensor no existe |
| 503 | Service Unavailable - BD no disponible |

---

## Validaciones

Antes de guardar readings, se valida:

✅ Building existe  
✅ Zone existe  
✅ Node existe  
✅ Sensor existe  
✅ Sensor type válido  
✅ Timestamp es válido  
✅ Valor dentro de rango (si aplica)

---

## Notas Importantes

- **MQTT Consumer está SIEMPRE escuchando** - Se inicia automáticamente
- **No hay endpoints para CREATE/UPDATE/DELETE** - Solo POST /telemetry/aggregate
- **Lecturas se guardan automáticamente** - No es necesario enviar POST /readings
- **La base de datos es compartida** - Monolito Consulta accede a los mismos datos
- **Timestamps deben ser UTC** - Usar formato ISO 8601 con Z (ej: 2026-10-20T18:00:00Z)

---

## Documentación Interactiva

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Troubleshooting

### "⚠️ No se pudo inicializar MQTT Consumer"
- Verificar que Mosquitto esté corriendo
- Verificar conectividad a broker
- Ver logs: `docker logs monolito-escucha`

### "Reading no se guarda"
- Verificar que sensor existe en BD
- Verificar que node existe en BD
- Revisar validaciones en TelemetryService

### "Database temporarily unavailable"
- PostgreSQL no está corriendo
- Verificar conexión a BD
- Ver logs: `docker logs postgres`

---

**Última actualización**: 2026-10-30  
**Versión**: 1.0  
**Estado**: ✅ Solo MQTT & Telemetría

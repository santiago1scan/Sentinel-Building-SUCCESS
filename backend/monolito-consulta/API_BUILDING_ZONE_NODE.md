# API Reference: Building, Zone, Node

Base URL: `http://localhost:8089`

---

## Building

### Create
**POST** `/buildings`

```json
{
  "name": "Edificio SB-001",
  "address": "Bogotá, Colombia"
}
```

**Response** `201 Created`
```json
{
  "building_id": 1,
  "name": "Edificio SB-001",
  "address": "Bogotá, Colombia"
}
```

---

### List All
**GET** `/buildings?limit=100&offset=0`

**Response** `200 OK`
```json
[
  {
    "building_id": 1,
    "name": "Edificio SB-001",
    "address": "Bogotá, Colombia"
  }
]
```

---

### Get by ID
**GET** `/buildings/{building_id}`

**Response** `200 OK`
```json
{
  "building_id": 1,
  "name": "Edificio SB-001",
  "address": "Bogotá, Colombia"
}
```

---

### Update
**PATCH** `/buildings/{building_id}`

```json
{
  "name": "Edificio SB-001 Actualizado",
  "address": "Nueva dirección"
}
```

**Response** `200 OK`
```json
{
  "building_id": 1,
  "name": "Edificio SB-001 Actualizado",
  "address": "Nueva dirección"
}
```

---

### Delete
**DELETE** `/buildings/{building_id}`

**Response** `204 No Content`

---

### Get Zones by Building
**GET** `/buildings/{building_id}/zones`

**Response** `200 OK`
```json
[
  {
    "zone_id": 1,
    "building_id": 1,
    "name": "Zona Piso 1",
    "floor": 1
  }
]
```

---

## Zone

### Create
**POST** `/zones`

```json
{
  "building_id": 1,
  "name": "Zona Piso 1",
  "floor": 1
}
```

**Response** `201 Created`
```json
{
  "zone_id": 1,
  "building_id": 1,
  "name": "Zona Piso 1",
  "floor": 1
}
```

---

### List All
**GET** `/zones?limit=100&offset=0`

**Response** `200 OK`
```json
[
  {
    "zone_id": 1,
    "building_id": 1,
    "name": "Zona Piso 1",
    "floor": 1
  }
]
```

---

### Get by ID
**GET** `/zones/{zone_id}`

**Response** `200 OK`
```json
{
  "zone_id": 1,
  "building_id": 1,
  "name": "Zona Piso 1",
  "floor": 1
}
```

---

### Update
**PATCH** `/zones/{zone_id}`

```json
{
  "building_id": 1,
  "name": "Zona Piso 1 Actualizada",
  "floor": 1
}
```

**Response** `200 OK`
```json
{
  "zone_id": 1,
  "building_id": 1,
  "name": "Zona Piso 1 Actualizada",
  "floor": 1
}
```

---

### Delete
**DELETE** `/zones/{zone_id}`

**Response** `204 No Content`

---

### Get by Building
**GET** `/zones/building/{building_id}`

**Response** `200 OK`
```json
[
  {
    "zone_id": 1,
    "building_id": 1,
    "name": "Zona Piso 1",
    "floor": 1
  }
]
```

---

## Node

### Create
**POST** `/nodes`

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

**Response** `201 Created`
```json
{
  "node_id": 1,
  "code": "NODE-FLOOR-1",
  "name": "Bridge 1 - Piso 1",
  "zone_id": 1,
  "ip_address": "192.168.1.10",
  "local_storage_mb": 1024,
  "last_signal_received_at": null,
  "registered_at": "2026-10-20T18:00:00Z"
}
```

---

### List All
**GET** `/nodes?limit=100&offset=0`

**Response** `200 OK`
```json
[
  {
    "node_id": 1,
    "code": "NODE-FLOOR-1",
    "name": "Bridge 1 - Piso 1",
    "zone_id": 1,
    "ip_address": "192.168.1.10",
    "local_storage_mb": 1024,
    "last_signal_received_at": null,
    "registered_at": "2026-10-20T18:00:00Z"
  }
]
```

---

### Get by ID
**GET** `/nodes/{node_id}`

**Response** `200 OK`
```json
{
  "node_id": 1,
  "code": "NODE-FLOOR-1",
  "name": "Bridge 1 - Piso 1",
  "zone_id": 1,
  "ip_address": "192.168.1.10",
  "local_storage_mb": 1024,
  "last_signal_received_at": null,
  "registered_at": "2026-10-20T18:00:00Z"
}
```

---

### Get by Code
**GET** `/nodes/code/{code}`

**Response** `200 OK`
```json
{
  "node_id": 1,
  "code": "NODE-FLOOR-1",
  "name": "Bridge 1 - Piso 1",
  "zone_id": 1,
  "ip_address": "192.168.1.10",
  "local_storage_mb": 1024,
  "last_signal_received_at": null,
  "registered_at": "2026-10-20T18:00:00Z"
}
```

---

### Update
**PATCH** `/nodes/{node_id}`

```json
{
  "code": "NODE-FLOOR-1",
  "name": "Bridge 1 - Piso 1 Actualizado",
  "zone_id": 1,
  "ip_address": "192.168.1.20",
  "local_storage_mb": 2048,
  "last_signal_received_at": "2026-10-20T18:30:00Z"
}
```

**Response** `200 OK`
```json
{
  "node_id": 1,
  "code": "NODE-FLOOR-1",
  "name": "Bridge 1 - Piso 1 Actualizado",
  "zone_id": 1,
  "ip_address": "192.168.1.20",
  "local_storage_mb": 2048,
  "last_signal_received_at": "2026-10-20T18:30:00Z",
  "registered_at": "2026-10-20T18:00:00Z"
}
```

---

### Delete
**DELETE** `/nodes/{node_id}`

**Response** `204 No Content`

---

### Get by Zone
**GET** `/nodes/zone/{zone_id}`

**Response** `200 OK`
```json
[
  {
    "node_id": 1,
    "code": "NODE-FLOOR-1",
    "name": "Bridge 1 - Piso 1",
    "zone_id": 1,
    "ip_address": "192.168.1.10",
    "local_storage_mb": 1024,
    "last_signal_received_at": null,
    "registered_at": "2026-10-20T18:00:00Z"
  }
]
```

---

### Get Node Sensors
**GET** `/nodes/{node_id}/sensors`

**Response** `200 OK`
```json
[
  {
    "sensor_id": 1,
    "code": "ADXL355-NODE-FLOOR-1",
    "primary_node_id": 1,
    "sensor_type_id": 1,
    "connection_type": "SPI",
    "connection_address": "0x1D"
  }
]
```

---

### Get Connectivity Logs
**GET** `/nodes/{node_id}/connectivity-logs`

**Response** `200 OK`
```json
[
  {
    "connectivity_id": 1,
    "node_id": 1,
    "started_at": "2026-10-20T18:00:00Z",
    "ended_at": null
  }
]
```

---

### Get Received Readings
**GET** `/nodes/{node_id}/received-readings`

**Response** `200 OK`
```json
[
  {
    "reading_id": 1,
    "sensor_id": 1,
    "receiving_node_id": 1,
    "measured_at": "2026-10-20T18:00:00Z",
    "received_at": "2026-10-20T18:00:01Z",
    "measured_value": 0.5,
    "sequence_number": 1
  }
]
```

---

## Quick cURL Examples

```bash
# Building
curl -X POST http://localhost:8089/buildings -H "Content-Type: application/json" -d '{"name":"Edificio SB-001","address":"Bogotá"}'
curl http://localhost:8089/buildings
curl http://localhost:8089/buildings/1
curl -X PATCH http://localhost:8089/buildings/1 -H "Content-Type: application/json" -d '{"name":"Nuevo nombre"}'
curl -X DELETE http://localhost:8089/buildings/1

# Zone
curl -X POST http://localhost:8089/zones -H "Content-Type: application/json" -d '{"building_id":1,"name":"Piso 1","floor":1}'
curl http://localhost:8089/zones
curl http://localhost:8089/zones/1
curl -X PATCH http://localhost:8089/zones/1 -H "Content-Type: application/json" -d '{"name":"Piso 1 Actualizado"}'
curl -X DELETE http://localhost:8089/zones/1
curl http://localhost:8089/zones/building/1

# Node
curl -X POST http://localhost:8089/nodes -H "Content-Type: application/json" -d '{"code":"NODE-FLOOR-1","name":"Bridge 1","zone_id":1,"ip_address":"192.168.1.10"}'
curl http://localhost:8089/nodes
curl http://localhost:8089/nodes/1
curl http://localhost:8089/nodes/code/NODE-FLOOR-1
curl -X PATCH http://localhost:8089/nodes/1 -H "Content-Type: application/json" -d '{"ip_address":"192.168.1.20"}'
curl -X DELETE http://localhost:8089/nodes/1
curl http://localhost:8089/nodes/zone/1
curl http://localhost:8089/nodes/1/sensors
curl http://localhost:8089/nodes/1/connectivity-logs
curl http://localhost:8089/nodes/1/received-readings
```

---

## Swagger UI

Interactive docs: `http://localhost:8089/docs`
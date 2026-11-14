# Registro de un nodo — paso a paso

Servicio: **monolito-consulta** (FastAPI). Base URL de ejemplo: `http://localhost:8089`.

## Autenticación

| Quién | Rutas | Cómo se autentica |
|---|---|---|
| **Bridge** (el nodo) | `POST /registrations`, `GET /registrations/{id}` | Sin token de Firebase. Usa el `poll_secret` en `X-Poll-Secret` |
| **Administrador** (panel web) | `GET /registrations/pending`, `GET /registrations/stream`, `POST /registrations/{id}/approve`, `POST /registrations/{id}/reject`, y el resto de la API (`/nodes`, `/zones`, `/buildings`, …) | `Authorization: Bearer <ID token de Firebase>` |

Sin token responde `401`; con un token válido de un usuario fuera de `FIREBASE_ADMIN_EMAILS`, `403`;
y si el servidor no tiene `FIREBASE_PROJECT_ID`, `503` (las rutas no quedan abiertas).
`EventSource` no puede enviar headers: en `GET /registrations/stream` el token también se acepta como
`?access_token=<ID token>`. Ese token queda en los registros de acceso; prefiere el header cuando puedas.

## Flujo general

```
Bridge                         API (consulta)                    Administrador (frontend)
  │  1. POST /registrations ───────►│                                   │
  │◄── 202 {registration_id,        │                                   │
  │         poll_secret}            │── SSE /registrations/stream ─────►│ (alerta de pendiente)
  │                                 │◄── 2. POST /{id}/approve ─────────│ {zone_id}
  │  3. GET /registrations/{id} ───►│   (crea el nodo, sin token aún)   │
  │◄── 200 {node_id,node_code,token}│   (genera token + cliente MQTT)   │
  │  4. Conecta a MQTT con el token │                                   │
```

Reglas clave:
- El nodo **no existe** hasta que el administrador aprueba.
- El **token se genera al recogerlo** (paso 3) y se entrega **una sola vez**.
- La solicitud (y la aprobación sin recoger) expira a los `REGISTRATION_TTL_SECONDS` (por defecto **300 s**).
- Las solicitudes viven **en memoria**: si el servicio se reinicia, el bridge debe volver a solicitar.

---

## Prerrequisito: edificio y zona

El administrador debe aprobar sobre una zona existente (`zone_id`).

**POST** `/buildings` → `201`
```json
{ "name": "Edificio SB-001", "address": "Bogotá, Colombia" }
```
```json
{ "building_id": 1, "name": "Edificio SB-001", "address": "Bogotá, Colombia" }
```

**POST** `/zones` → `201`
```json
{ "building_id": 1, "name": "Zona Piso 1", "floor": 1 }
```
```json
{ "zone_id": 1, "building_id": 1, "name": "Zona Piso 1", "floor": 1 }
```

---

## Paso 1 — El bridge solicita el registro

**POST** `/registrations`

```json
{
  "code": "NODE-001",
  "name": "Nodo sala de servidores",
  "building_code": "SB-001",
  "zone_code": "ZONA-P1"
}
```

| Campo           | Tipo   | Reglas        |
|-----------------|--------|---------------|
| `code`          | string | 1–100 chars, único entre nodos |
| `name`          | string | 1–150 chars   |
| `building_code` | string | 1–50 chars    |
| `zone_code`     | string | 1–50 chars (informativo; la zona real la elige el admin) |

**Respuesta `202 Accepted`**
```json
{
  "registration_id": "3f2a9c1e7b4d4e0f9a6b5c8d1e2f3a4b",
  "poll_secret": "Xk9...secreto-url-safe...",
  "status": "pending",
  "expires_at": "2026-11-13T15:05:00Z"
}
```

> ⚠️ `poll_secret` **solo se muestra aquí**. El bridge debe guardarlo.

Errores: `409` (ya existe un nodo con ese `code`, o ya hay una solicitud abierta para él), `422` (payload inválido).

---

## Paso 2 — El administrador revisa y aprueba

### 2a. Ver pendientes

**GET** `/registrations/pending` → `200`
```json
[
  {
    "registration_id": "3f2a9c1e7b4d4e0f9a6b5c8d1e2f3a4b",
    "code": "NODE-001",
    "name": "Nodo sala de servidores",
    "building_code": "SB-001",
    "zone_code": "ZONA-P1",
    "status": "pending",
    "created_at": "2026-11-13T15:00:00Z",
    "expires_at": "2026-11-13T15:05:00Z"
  }
]
```

### 2b. (Opcional) Recibirlas en vivo por SSE

**GET** `/registrations/stream` (`text/event-stream`)

Emite la lista al conectar y en cada cambio; envía `: keepalive` cada 15 s.
```
event: pending
data: [{"registration_id":"3f2a...","code":"NODE-001", ...}]
```

```js
const es = new EventSource("http://localhost:8089/registrations/stream");
es.addEventListener("pending", (e) => setPending(JSON.parse(e.data)));
```

### 2c. Aprobar

**POST** `/registrations/{registration_id}/approve`
```json
{ "zone_id": 1 }
```
`zone_id` debe ser entero > 0 y existir.

**Respuesta `200 OK`**
```json
{
  "registration_id": "3f2a9c1e7b4d4e0f9a6b5c8d1e2f3a4b",
  "status": "approved",
  "node_id": 12,
  "zone_id": 1
}
```
Al aprobar se crea el nodo (sin token) y se renueva el plazo de expiración.

Errores: `404` (solicitud o zona inexistente), `409` (la solicitud ya no está `pending`, o el nodo ya existe).

### 2d. Rechazar (alternativa)

**POST** `/registrations/{registration_id}/reject` (sin body) → `200`
```json
{
  "registration_id": "3f2a9c1e7b4d4e0f9a6b5c8d1e2f3a4b",
  "code": "NODE-001",
  "name": "Nodo sala de servidores",
  "building_code": "SB-001",
  "zone_code": "ZONA-P1",
  "status": "rejected",
  "created_at": "2026-11-13T15:00:00Z",
  "expires_at": "2026-11-13T15:05:00Z"
}
```

---

## Paso 3 — El bridge recoge el token (polling)

**GET** `/registrations/{registration_id}`
Header obligatorio: `X-Poll-Secret: <poll_secret del paso 1>`

```bash
curl -H "X-Poll-Secret: Xk9..." \
     http://localhost:8089/registrations/3f2a9c1e7b4d4e0f9a6b5c8d1e2f3a4b
```

| Situación | Código | Body |
|---|---|---|
| Aún pendiente | `202` | `{"status": "pending"}` → reintentar (p. ej. cada 2–5 s) |
| Aprobada (primera vez) | `200` | ver abajo |
| Secreto incorrecto / id inexistente | `404` | mismo mensaje en ambos casos |
| Rechazada, expirada o ya entregada | `410` | token no disponible |
| Broker MQTT no disponible | `503` | la solicitud sigue aprobada; reintentar genera otro token |

**Respuesta `200 OK` (única vez)**
```json
{
  "node_id": 12,
  "node_code": "NODE-001",
  "token": "tok_..."
}
```

> ⚠️ Guardar el `token` de inmediato: un segundo GET responde `410`.

Internamente, al entregar: se guarda el hash del token en BD y luego se crea en el broker un rol y un cliente MQTT para el nodo.

---

## Paso 4 — El nodo publica por MQTT

Credenciales MQTT:
- **username**: `node_code` (ej. `NODE-001`)
- **password**: el `token` recibido
- **host/puerto**: `MQTT_HOST` / `MQTT_PORT` (por defecto `mosquitto:1883`)

Permiso: solo **publicar** en su propio topic:

```
sentinel/v1/{building_code}/{node_code}/telemetry/aggregate
# ej.: sentinel/v1/SB-001/NODE-001/telemetry/aggregate
```

`building_code` es el configurado en el servidor (`BUILDING_CODE`, por defecto `SB-001`).

---

## Estados de una solicitud

| Estado | Significado |
|---|---|
| `pending` | Esperando revisión del administrador |
| `approved` | Nodo creado; el token aún no se ha recogido |
| `rejected` | Rechazada por el administrador |
| `delivered` | Token ya entregado (no se repite) |
| `expired` | Venció el plazo (`pending` o `approved` sin recoger) |

## Formato de error

```json
{
  "status": 409,
  "error": "ConflictError",
  "message": "Ya existe un nodo con código NODE-001",
  "path": "/registrations",
  "request_id": "a1b2c3d4"
}
```

## CORS

CORS está abierto: cualquier origen, método y header (`Authorization`, `X-Poll-Secret`, …), sin credenciales. Para limitarlo a un panel concreto define `CORS_ORIGINS` (separados por coma), por ejemplo `CORS_ORIGINS=https://panel.ejemplo.com`.

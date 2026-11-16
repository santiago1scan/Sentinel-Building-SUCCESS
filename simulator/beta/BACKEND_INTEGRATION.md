# Integración con el backend

La Beta envía un JSON 2.0 independiente por bridge a:

```text
POST /telemetry/aggregate
```

El backend debe responder con un código `2xx` y el siguiente cuerpo:

```json
{
  "message_uid": "mismo-uid-recibido",
  "readings_created": 4,
  "errors": []
}
```

El bridge conserva el mensaje en la cola hasta recibir esta confirmación.
Un respaldo recibido por LoRa no elimina el pendiente del backend.

## Identificadores utilizados

Nodos:

- `NODE-FLOOR-1`
- `NODE-FLOOR-2`

Sensores de cada nodo:

- `ADXL355-NODE-FLOOR-N`
- `AMG8833-NODE-FLOOR-N`
- `BME688-NODE-FLOOR-N`
- `INA219-NODE-FLOOR-N`

El backend debe registrar previamente esos nodos y sensores. También debe
tratar `message_uid` como identificador único para que un reintento no cree
lecturas duplicadas.

## Ejecución local

```powershell
$env:SENTINEL_BACKEND_URL = "http://127.0.0.1:8089"
$env:SENTINEL_NODE_TOKEN_FLOOR_1 = "token-nodo-1"
$env:SENTINEL_NODE_TOKEN_FLOOR_2 = "token-nodo-2"
python start_beta.py
```

Si la Beta se ejecuta en Docker y el backend se encuentra en otro contenedor,
la URL debe usar el nombre del servicio accesible desde esa red, por ejemplo:

```text
http://monolito-escucha:8089
```

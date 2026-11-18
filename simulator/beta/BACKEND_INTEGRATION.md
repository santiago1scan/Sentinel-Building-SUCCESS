# Integración con el backend local

La Beta envía un JSON 2.0 independiente por bridge al mock backend:

```text
POST /api/v1/telemetry/aggregate
```

El dashboard principal consulta `GET /api/v1/sensors/latest` y combina el
estado más reciente por nodo y tipo de sensor. Una lectura anómala reciente
prevalece sobre una normal de la otra simulación; el valor normal de la misma
fuente restablece el sensor. Lecturas con más de 90 segundos se marcan como
obsoletas para que una alarma histórica no siga activa si su simulador se
detiene sin enviar un `clear`.

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

El mock backend almacena el agregado completo en SQLite en
`simulator\data_api\api_received.db`. No requiere registrar nodos, sensores ni
tokens.

## Ejecución local

```powershell
# En una terminal, desde la raíz Sentinel-Building-SUCCESS:
Set-Location .\simulator
py -m uvicorn mock_backend.fastapi_app:app --host 127.0.0.1 --port 8000

# En otra terminal, desde simulator\beta:
py .\start_beta.py --backend-url "http://127.0.0.1:8000/api/v1"
```

El simulador añade `/telemetry/aggregate` a la URL base. Los agregados se
mantienen en la cola SQLite de Beta hasta que el mock confirma el mismo
`message_uid` y la cantidad de sensores recibidos. Las muestras crudas de la
Beta no se persisten en el mock.

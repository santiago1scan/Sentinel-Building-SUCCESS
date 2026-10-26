# Bridge simulado

Este proceso representa la Raspberry Pi de cada nodo. Recibe las lecturas
internas del simulador, conserva los datos originales en SQLite, calcula el
JSON agregado y lo entrega al backend central.

## Flujo

```text
simulador de sensores -> POST local /v1/readings -> bridge
bridge -> REST: datos nuevos
bridge -> MQTT: datos pendientes después de una desconexión
bridge -> LoRa: resumen para el brigadista cuando no hay conectividad
```

El JSON enviado al backend conserva el contrato estándar existente. El bridge
solo agrega los metadatos de entrega (`delivery_status`, `transport` y
`sent_at`) al momento de elegir el canal.

## Ejecutar

Desde la raíz del proyecto:

```powershell
python .\bridge\bridge_service.py `
  --api-url "http://127.0.0.1:8000" `
  --data-dir "data_bridge"
```

Luego, en otra terminal:

```powershell
python .\mqtt_sensor_simulator.py `
  --bridge-url "http://127.0.0.1:8766" `
  --interval 30
```

Para HiveMQ, se configuran las credenciales mediante variables de entorno. No
se deben subir contraseñas, tokens ni bases SQLite al repositorio.

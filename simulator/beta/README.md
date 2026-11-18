# Sentinel Building — Beta Simulation

Versión autocontenida de la simulación Beta de Sentinel Building. Esta carpeta
no modifica el backend del equipo ni depende de las versiones anteriores del
simulador.

El resumen del trabajo de integración de ambos simuladores está en
[`../RESUMEN_CAMBIOS.md`](../RESUMEN_CAMBIOS.md).

## Funciones implementadas

- Dos bridges independientes: `NODE-FLOOR-1` y `NODE-FLOOR-2`.
- Cuatro sensores virtuales por bridge: ADXL355, AMG8833, BME688 e INA219.
- Lecturas crudas procesadas únicamente en memoria.
- Cálculo y persistencia de resúmenes JSON 2.0 en SQLite.
- Límite de almacenamiento configurable, por defecto setenta por ciento.
- Rotación de resúmenes entregados sin eliminar mensajes pendientes.
- Sincronización REST opcional y fallback LoRa simulado.
- Reintentos cronológicos y deduplicación por `message_uid`.
- Dashboard React local con controles, imágenes, GIF y modelo 3D.
- Pruebas automáticas de almacenamiento, rotación y recuperación.

## Requisitos

- Python 3.11 o superior.
- Navegador moderno.
- Conexión a Internet para cargar React y `model-viewer` desde CDN.
- Para el mock SQLite, FastAPI y Uvicorn; para MQTT, `paho-mqtt` es opcional.
  Las dependencias compartidas están en `simulator\requirements.txt`.

## Inicio rápido

Desde esta carpeta:

```powershell
python start_beta.py --control-port 8792
```

El comando inicia:

- Dashboard principal: `http://127.0.0.1:8782`
- Simulador y API de control: `http://127.0.0.1:8792`

El navegador se abre automáticamente. Para detener ambos procesos, presione
`Ctrl+C` en la terminal.

El puerto de control `8792` evita el conflicto con el panel de escenarios,
que utiliza `8790`.

En Windows también puede iniciar toda la Beta haciendo doble clic en
`INICIAR_BETA.bat`. La carpeta es portable: no contiene rutas absolutas del
equipo de desarrollo.

## Ejecución con Docker

Si Docker está instalado, no es necesario instalar Python en el equipo host:

```powershell
docker compose up --build
```

Después abra `http://127.0.0.1:8782`. Para detenerla:

```powershell
docker compose down
```

Las imágenes, GIF, logos institucionales, fotografías de sensores y el modelo
3D se incluyen en `dashboard/assets`. React, Babel y el componente del visor 3D
se cargan desde CDN, por lo que el panel requiere conexión a Internet.

## Ejecutar pruebas

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

## Conectar el mock backend local

El mock backend recibe los agregados de ambos simuladores y los guarda en
SQLite (`simulator\data_api\api_received.db`). Inícialo primero en una terminal
desde la raíz del proyecto:

```powershell
Set-Location .\simulator
py -m uvicorn mock_backend.fastapi_app:app --host 127.0.0.1 --port 8000
```

En otra terminal, inicia la Beta. La URL predeterminada es
`http://127.0.0.1:8000/api/v1`; también se puede indicar explícitamente:

```powershell
Set-Location .\simulator\beta
py .\start_beta.py --backend-url "http://127.0.0.1:8000/api/v1"
```

El motor añade `/telemetry/aggregate` y conserva el contrato JSON 2.0. Los
tokens no son necesarios con el mock local. Un agregado solo sale de la cola
cuando el mock confirma el mismo `message_uid` y todos sus sensores. Si el
mock todavía no está disponible, los mensajes siguen pendientes en SQLite y
se reintentan en orden al iniciar la simulación. El contrato está documentado en
[`BACKEND_INTEGRATION.md`](BACKEND_INTEGRATION.md).

El dashboard Beta consulta `GET /api/v1/sensors/latest` para mostrar el estado
más reciente de ambas simulaciones. Las anomalías recientes de escenarios
prevalecen sobre lecturas normales de Beta hasta que el escenario envíe valores
normales; los datos con más de 90 segundos se marcan como obsoletos.

## Estructura

```text
Beta/
├── README.md
├── ASSETS.md
├── requirements.txt
├── start_beta.py
├── beta_simulator/          # Modelos de sensores y contrato JSON 2.0
├── simulator_v2/            # Bridges, SQLite, LoRa, REST y API de control
├── dashboard_react_v2/      # Servidor y aplicación web
├── dashboard/assets/        # Imágenes, GIF, logos y modelo GLB
├── tests/                   # Pruebas automáticas de resiliencia
└── data/                    # Datos locales; no se versionan
```

## Estado del alcance

La Beta incluye almacenamiento offline, sincronización, deduplicación y LoRa
simulado. El descubrimiento automático de nodos vecinos de la US14 y el modelo
energético de batería/LoRa de SCRUM-111 siguen pendientes.


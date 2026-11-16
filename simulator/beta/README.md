# Sentinel Building — Beta Simulation

Versión autocontenida de la simulación Beta de Sentinel Building. Esta carpeta
no modifica el backend del equipo ni depende de las versiones anteriores del
simulador.

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

No se necesitan paquetes externos de Python para la versión actual.

## Inicio rápido

Desde esta carpeta:

```powershell
python start_beta.py
```

El comando inicia:

- Simulador y API de control: `http://127.0.0.1:8790`
- Dashboard: `http://127.0.0.1:8782`

El navegador se abre automáticamente. Para detener ambos procesos, presione
`Ctrl+C` en la terminal.

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

## Conectar un backend

El simulador funciona sin backend y usa el receptor LoRa local. Para una futura
integración, ejecute el motor directamente con la URL base autorizada:

```powershell
$env:SENTINEL_NODE_TOKEN_FLOOR_1 = "token-del-nodo-1"
$env:SENTINEL_NODE_TOKEN_FLOOR_2 = "token-del-nodo-2"
python start_beta.py --backend-url "http://127.0.0.1:8089"
```

El motor añade `/telemetry/aggregate`, envía un `X-Node-Token` diferente por
bridge y conserva el contrato JSON 2.0. Un mensaje solo sale de la cola cuando
el backend confirma el mismo `message_uid`, no reporta errores y registra todas
las lecturas esperadas.

También puede copiar `.env.example` a `.env` y definir
`SENTINEL_BACKEND_URL`. Los identificadores que el backend debe registrar y el
formato exacto de la confirmación están documentados en
[`BACKEND_INTEGRATION.md`](BACKEND_INTEGRATION.md).

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


# Sentinel Building Simulator

Aquí dejé integrada la versión Beta que he estado probando. Conservé la estructura de tres capas que ya tenía el equipo y agregué mis módulos en el lugar que les corresponde, sin mover el backend ni el frontend.

## Cómo lo organicé

- `simulator/app/datos`: generación de los cuatro sensores y comunicación con cada bridge.
- `simulator/app/negocio`: ciclo de simulación, anomalías y controles.
- `simulator/app/presentacion`: dashboard, imágenes, GIF y modelo 3D.
- `bridge/app/datos`: SQLite y canal LoRa virtual.
- `bridge/app/negocio`: agregación JSON 2.0, cola pendiente, REST y decisión de contingencia.
- `bridge/app/presentacion`: API de control y consulta del bridge.
- `brigadist-receiver`: emulador para la demostración y firmware base para el Heltec.
- `protocol-contract`: formato binario que comparten el bridge y el receptor.

El mismo código del bridge se inicia dos veces. Cada ejecución representa una Raspberry Pi y mantiene su propia base SQLite.

## Ejecutar mi versión completa

Desde esta carpeta:

```powershell
python start_operational.py
```

También se puede abrir `INICIAR_SIMULATOR.bat`.

Direcciones que uso en local:

- Dashboard: `http://127.0.0.1:8982`
- Bridge del piso 1: `http://127.0.0.1:8991`
- Bridge del piso 2: `http://127.0.0.1:8992`
- Receptor del brigadista: `http://127.0.0.1:8993`

Para probar con un backend local agrego su dirección:

```powershell
python start_operational.py --backend-url http://127.0.0.1:8000
```

## Flujo que estoy representando

```text
Sensores -> Bridge Raspberry Pi 5
              |-> SQLite/microSD
              |-> REST/backend
              `-> LoRa/SX1262 -> receptor Heltec del brigadista
```

Los sensores solo producen y envían lecturas. El bridge es quien valida, calcula los resúmenes, forma el JSON 2.0 y guarda la cola. Si una emergencia no recibe confirmación REST, envío una trama LoRa compacta al brigadista. Ese ACK de radio no borra el pendiente del backend; el JSON queda guardado hasta recuperar la conexión.

## Pruebas

```powershell
cd bridge
python -m pytest tests -q

cd ..\simulator
python -m pytest tests -q

cd ..\brigadist-receiver\emulator
python -m pytest tests -q
```

Estas pruebas revisan la generación de sensores, la cola local, la recuperación en orden, el aislamiento de bridges y la autenticación de la trama LoRa. Los archivos generados durante la ejecución quedan en `runtime/` y no se suben al repositorio.

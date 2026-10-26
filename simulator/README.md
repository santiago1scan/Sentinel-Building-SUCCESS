# Sentinel Building Simulator

This folder contains the sensor simulator and the bridge process used to test
the Sentinel Building data flow.

## Components

- `mqtt_sensor_simulator.py`: generates readings for the virtual sensors.
- `bridge/bridge_service.py`: receives readings, stores them locally and
  prepares the standard telemetry message.
- `telemetry_standard.py`: builds the standard JSON and calculates the window
  averages.
- `virtual_lora.py`: simulates the LoRa link used during disconnection.
- `mock_backend/fastapi_app.py`: local FastAPI endpoint for testing.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run the local test

Start the mock backend:

```powershell
python -m uvicorn mock_backend.fastapi_app:app --host 127.0.0.1 --port 8000
```

In another terminal, start the bridge:

```powershell
python .\bridge\bridge_service.py `
  --api-url "http://127.0.0.1:8000" `
  --listen-port 8766 `
  --data-dir "data_bridge"
```

In a third terminal, start the simulator:

```powershell
python .\mqtt_sensor_simulator.py `
  --bridge-url "http://127.0.0.1:8766" `
  --interval 30 `
  --data-dir "data_sensor_simulator"
```

The simulator sends raw readings to `POST /v1/readings` on the bridge. The
bridge stores the readings in SQLite, calculates the aggregate and sends new
data through REST. Pending data is kept locally for MQTT recovery. LoRa is
used for the emergency summary when the network is unavailable.

Do not commit passwords, tokens, virtual environments or generated databases.

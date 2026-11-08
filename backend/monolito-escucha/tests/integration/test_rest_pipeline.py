"""Integración REST: simulador → bridge → monolito-escucha, verificado con monolito-consulta.

Las lecturas se comprueban con la API de consulta (GET /readings/receiving-node/{id}),
no con SQL directo. Así la prueba valida lo que ve el sistema, no lo que hay en la tabla.

ATENCIÓN: esta prueba escribe lecturas reales en el stack que apunta. Está desactivada
por defecto. Para correrla con Docker (recomendado):

    docker compose --profile test run --rm integration-tests

Para correrla desde el host, con el stack ya levantado:

    RUN_INTEGRATION=1 pytest tests/integration -v

Precondiciones:
- Migración aplicada (columna node.token_hash) y tokens provisionados para los nodos.
- SENTINEL_NODE_TOKENS con los mismos tokens que tienen los nodos en la BD.
- Stack corriendo: monolito-escucha, monolito-consulta y bridge. Con
  SENTINEL_INTEGRATION_COMPOSE=1 la prueba los levanta con docker compose antes de correr.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

RUN_INTEGRATION = os.getenv("RUN_INTEGRATION") == "1"
pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION, reason="Integración desactivada: define RUN_INTEGRATION=1"
)

REPO = Path(__file__).resolve().parents[4] if len(Path(__file__).resolve().parents) > 4 else None
# Dentro del contenedor de pruebas el simulador se monta en /simulator.
SIM_DIR = Path(os.getenv("INTEGRATION_SIMULATOR_DIR") or (REPO / "simulator"))
ESCUCHA_URL = os.getenv("INTEGRATION_ESCUCHA_URL", "http://localhost:8089")
CONSULTA_URL = os.getenv("INTEGRATION_CONSULTA_URL", "http://localhost:8090")
BRIDGE_URL = os.getenv("INTEGRATION_BRIDGE_URL", "http://localhost:8766")
NODES = ["NODE-FLOOR-1", "NODE-FLOOR-2"]
# Margen para diferencias de reloj entre el host de la prueba y el servidor.
CLOCK_SKEW = timedelta(seconds=5)


def _get_json(url: str, timeout: float = 5):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read())


def _wait_for(url: str, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            _get_json(url, timeout=3)
            return
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
            time.sleep(1)
    pytest.fail(f"{url} no responde tras {timeout}s: {last_error}")


def _node_id(code: str) -> int:
    """Identificador del nodo según consulta."""
    return _get_json(f"{CONSULTA_URL}/nodes/code/{code}")["node_id"]


def _readings_received_since(code: str, since: datetime) -> int:
    """Lecturas que consulta reporta para el nodo receptor, recibidas desde `since`."""
    node_id = _node_id(code)
    readings = _get_json(f"{CONSULTA_URL}/readings/receiving-node/{node_id}?limit=1000")
    cutoff = since - CLOCK_SKEW
    return sum(
        1 for reading in readings
        if datetime.fromisoformat(reading["received_at"]) >= cutoff
    )


def _readings_total(code: str) -> int:
    node_id = _node_id(code)
    return len(_get_json(f"{CONSULTA_URL}/readings/receiving-node/{node_id}?limit=1000"))


def _run_simulator_one_cycle(data_dir: Path, timeout: float = 90) -> tuple[str, bool]:
    """Arranca el simulador en modo bridge y espera la primera línea de ciclo."""
    # PYTHONUNBUFFERED: sin esto la salida va a un pipe con búfer y la línea de ciclo
    # no llega a la prueba (en Docker el contenedor ya lo define).
    process = subprocess.Popen(
        [
            sys.executable, "-u", "mqtt_sensor_simulator.py",
            "--bridge-url", BRIDGE_URL, "--interval", "30", "--data-dir", str(data_dir),
        ],
        cwd=SIM_DIR, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    lines: list[str] = []
    cycle_seen = threading.Event()

    def read_output() -> None:
        for line in process.stdout:
            lines.append(line)
            if line.startswith("cycle="):
                cycle_seen.set()

    threading.Thread(target=read_output, daemon=True).start()
    try:
        process.stdin.write("status\n")
        process.stdin.flush()
        completed = cycle_seen.wait(timeout)
    finally:
        process.terminate()
        process.wait(timeout=10)
    return "".join(lines), completed


@pytest.fixture(scope="module")
def stack():
    if os.getenv("SENTINEL_INTEGRATION_COMPOSE") == "1":
        assert REPO is not None, "SENTINEL_INTEGRATION_COMPOSE solo funciona desde el repo, no en contenedor"
        subprocess.run(
            ["docker", "compose", "up", "-d", "--build",
             "monolito-escucha", "monolito-consulta", "bridge"],
            cwd=REPO, check=True,
        )
    _wait_for(f"{ESCUCHA_URL}/health")
    _wait_for(f"{CONSULTA_URL}/health")
    _wait_for(f"{BRIDGE_URL}/health")
    return True


def test_simulator_cycle_is_received_by_backend(stack, tmp_path):
    started = datetime.now(UTC)

    output, completed = _run_simulator_one_cycle(tmp_path)

    assert completed, f"el simulador no completó un ciclo:\n{output}"
    match = re.search(r"rest=(\d+)", output)
    assert match is not None, f"la salida del simulador no trae el resultado REST:\n{output}"
    assert int(match.group(1)) == len(NODES), (
        f"el bridge entregó por REST {match.group(1)} de {len(NODES)} nodos:\n{output}"
    )

    # Consulta debe ver las lecturas nuevas de ambos nodos. Se reintenta porque el
    # procesamiento en escucha es asíncrono respecto a la respuesta 202 del bridge.
    deadline = time.monotonic() + 30
    received = {code: _readings_received_since(code, started) for code in NODES}
    while time.monotonic() < deadline and not all(received.values()):
        time.sleep(1)
        received = {code: _readings_received_since(code, started) for code in NODES}

    assert all(received.values()), (
        f"consulta no reporta lecturas nuevas para todos los nodos: {received}"
    )


def test_rest_without_node_token_is_rejected_and_nothing_is_received(stack):
    sys.path.insert(0, str(SIM_DIR))
    import mqtt_sensor_simulator as sim
    import telemetry_standard

    readings = []
    for node in sim.NODES:
        readings.extend(sim.readings_for(node, 1, set()))
    aggregate = telemetry_standard.aggregate_readings(readings, "SB-001", 30.0, 1, sim.NODES)

    before = {code: _readings_total(code) for code in NODES}
    request = urllib.request.Request(
        ESCUCHA_URL + "/telemetry/aggregate",
        data=json.dumps(aggregate).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request, timeout=10)

    assert error.value.code == 401
    assert {code: _readings_total(code) for code in NODES} == before

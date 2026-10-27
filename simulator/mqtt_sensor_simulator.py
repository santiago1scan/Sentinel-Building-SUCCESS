"""Simulador MQTT de sensores para Sentinel Building.

Genera eventos legibles, los guarda primero en una outbox SQLite local y,
si el broker MQTT está disponible, los publica con QoS 1. Si MQTT se cae,
los eventos permanecen pendientes y se reintentan al recuperar la conexión.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
import ssl
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from virtual_lora import DeliveryResult, VirtualRadioChannel
from telemetry_standard import aggregate_readings

try:
    import paho.mqtt.client as mqtt
except ModuleNotFoundError:  # Dejo el modo dry-run disponible aunque no tenga MQTT instalado.
    mqtt = None


BUILDING_ID = "SB-001"
NODES = {
    # Por ahora uso estas coordenadas de prueba para ubicar el edificio.
    # Después las cambio cuando tengamos la ubicación definitiva.
    "NODE-FLOOR-1": {
        "zone_id": "ZONE-F1", "floor": 1,
        "bridge_name": "Bridge 1 - Piso 1",
        "latitude": 4.7110, "longitude": -74.0721,
    },
    "NODE-FLOOR-2": {
        "zone_id": "ZONE-F2", "floor": 2,
        "bridge_name": "Bridge 2 - Piso 2",
        "latitude": 4.7112, "longitude": -74.0721,
    },
}

SENSORS = {
    "accelerometer": {"model": "ADXL355", "interface": "SPI", "unit": "g"},
    "thermal_array": {"model": "AMG8833", "interface": "I2C", "unit": "degC"},
    "gas_environmental": {"model": "BME688", "interface": "I2C", "unit": "mixed"},
    "power_monitor": {"model": "INA219", "interface": "I2C", "unit": "mixed"},
}

SENSOR_PREFIX = {
    "accelerometer": "ADXL355",
    "thermal_array": "GRID-EYE",
    "gas_environmental": "BME688",
    "power_monitor": "INA219",
}

TOPIC_ROOT = "sentinel/v1"
BATCH_TOPIC = f"{TOPIC_ROOT}/{BUILDING_ID}/telemetry/batch"
EMERGENCY_TOPIC = f"{TOPIC_ROOT}/{BUILDING_ID}/emergency"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sensor (
    sensor_id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL,
    zone_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    model TEXT NOT NULL,
    interface TEXT NOT NULL,
    sampling_interval_s REAL NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS outbox (
    event_id TEXT PRIMARY KEY,
    sensor_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    priority TEXT NOT NULL,
    quality TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    topic TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    published_at TEXT,
    FOREIGN KEY(sensor_id) REFERENCES sensor(sensor_id)
);
CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status, generated_at);
CREATE TABLE IF NOT EXISTS batch_outbox (
    batch_id TEXT PRIMARY KEY,
    generated_at TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    priority TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    topic TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    published_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_batch_outbox_status ON batch_outbox(status, generated_at);
CREATE TABLE IF NOT EXISTS aggregate_outbox (
    message_uid TEXT PRIMARY KEY,
    generated_at TEXT NOT NULL,
    priority TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    sent_at TEXT,
    response TEXT
);
CREATE INDEX IF NOT EXISTS idx_aggregate_outbox_status ON aggregate_outbox(status, generated_at);
CREATE TABLE IF NOT EXISTS connectivity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_at TEXT NOT NULL,
    state TEXT NOT NULL,
    detail TEXT NOT NULL
);
"""


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def open_store(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=FULL")
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=5000")
    con.executescript(SCHEMA)
    con.commit()
    return con


def sensor_id(node_id: str, sensor_type: str) -> str:
    return f"{SENSOR_PREFIX[sensor_type]}-{node_id}"


def topic_for(node_id: str, sensor_id_value: str) -> str:
    return f"{TOPIC_ROOT}/{BUILDING_ID}/{node_id}/{sensor_id_value}/reading"


def select_transport(node_id: str, bridge_state: dict[str, bool],
                     lora_state: dict[str, bool], mesh_state: bool) -> str | None:
    """Aquí decido por qué ruta intento enviar cada evento.

    Primero pruebo LoRa, después mesh y, si no hay ruta, dejo el dato local.
    """
    if not bridge_state.get(node_id, False):
        return None
    if lora_state.get(node_id, False):
        return "lora"
    if mesh_state:
        return "ieee802154_mesh"
    return None


def register_catalog(con: sqlite3.Connection) -> None:
    rows = []
    for node_id, node in NODES.items():
        for sensor_type, definition in SENSORS.items():
            rows.append((sensor_id(node_id, sensor_type), node_id, node["zone_id"],
                         sensor_type, definition["model"], definition["interface"], 30.0, 1))
    con.executemany("""INSERT OR IGNORE INTO sensor
        (sensor_id, node_id, zone_id, sensor_type, model, interface,
         sampling_interval_s, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", rows)
    con.commit()


def event_envelope(node_id: str, sensor_type: str, sequence: int,
                   payload: dict[str, Any], priority: str = "normal",
                   quality: str = "valid") -> dict[str, Any]:
    node = NODES[node_id]
    sid = sensor_id(node_id, sensor_type)
    return {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "event_type": "sensor_reading",
        "building_id": BUILDING_ID,
        "node_id": node_id,
        "zone_id": node["zone_id"],
        "floor": node["floor"],
        "bridge_name": node["bridge_name"],
        "latitude": node["latitude"],
        "longitude": node["longitude"],
        "sensor_id": sid,
        "sensor_type": sensor_type,
        "sensor_model": SENSORS[sensor_type]["model"],
        "generated_at": now_utc(),
        "sequence_number": sequence,
        "priority": priority,
        "quality": quality,
        # Las lecturas normales esperan el intervalo. Si aparece una emergencia,
        # la envío de una vez sin esperar el siguiente ciclo.
        "delivery_policy": "immediate" if priority in {"high", "critical"} else "periodic",
        "transport": "mqtt",
        "payload": payload,
    }


def readings_for(node_id: str, sequence: int, anomalies: set[str]) -> list[dict[str, Any]]:
    anomaly = "accelerometer" in anomalies
    readings = [event_envelope(node_id, "accelerometer", sequence, {
        "x_g": round(random.uniform(-0.02, 0.02) if not anomaly else random.uniform(-0.7, 0.7), 4),
        "y_g": round(random.uniform(-0.02, 0.02) if not anomaly else random.uniform(-0.7, 0.7), 4),
        "z_g": round(random.uniform(0.98, 1.02) if not anomaly else random.uniform(0.6, 1.6), 4),
        "rms_g": round(random.uniform(0.001, 0.01) if not anomaly else random.uniform(0.25, 0.8), 4),
        "frequency_hz": round(random.uniform(0.1, 1.0) if not anomaly else random.uniform(1, 8), 2),
    }, "critical" if anomaly else "normal", "simulated_anomaly" if anomaly else "valid")]

    hot = "thermal_array" in anomalies
    matrix = [[round(random.uniform(23.5, 27.0), 2) for _ in range(8)] for _ in range(8)]
    if hot:
        for row, col in ((3, 3), (3, 4), (4, 3), (4, 4)):
            matrix[row][col] = round(random.uniform(45, 60), 2)
    readings.append(event_envelope(node_id, "thermal_array", sequence, {
        "matrix_size": "8x8", "pixels_c": matrix,
        "maximum_c": max(max(row) for row in matrix),
        "average_c": round(sum(sum(row) for row in matrix) / 64, 2),
        "hot_pixels": sum(value >= 40 for row in matrix for value in row),
    }, "high" if hot else "normal", "simulated_anomaly" if hot else "valid"))

    gas = "gas_environmental" in anomalies
    readings.append(event_envelope(node_id, "gas_environmental", sequence, {
        "temperature_c": round(random.uniform(22, 27) if not gas else random.uniform(30, 42), 2),
        "humidity_percent": round(random.uniform(45, 65) if not gas else random.uniform(70, 90), 2),
        "pressure_hpa": round(random.uniform(995, 1020), 2),
        "iaq_index": random.randint(20, 120) if not gas else random.randint(250, 500),
        "tvoc_ppb": random.randint(50, 350) if not gas else random.randint(900, 3000),
    }, "high" if gas else "normal", "simulated_anomaly" if gas else "valid"))

    power = "power_monitor" in anomalies
    voltage = random.uniform(11.8, 12.6) if not power else random.uniform(10.2, 11.0)
    current = random.uniform(650, 1000) if not power else random.uniform(900, 1500)
    readings.append(event_envelope(node_id, "power_monitor", sequence, {
        "bus_voltage_v": round(voltage, 3),
        "current_ma": round(current, 2),
        "power_mw": round(voltage * current, 2),
        "power_source": "main" if not power else "battery",
        "battery_low": voltage < 11,
    }, "critical" if power else "normal", "simulated_anomaly" if power else "valid"))
    return readings


def batch_envelope(readings: list[dict[str, Any]], sequence: int) -> dict[str, Any]:
    """Junto las lecturas de los dos bridges en un solo paquete JSON.

    El bridge recibe las lecturas individuales y arma el paquete antes de
    enviarlo al backend.
    """
    by_node: dict[str, dict[str, Any]] = {}
    for event in readings:
        node_id = event["node_id"]
        node = NODES[node_id]
        entry = by_node.setdefault(node_id, {
            "node_id": node_id,
            "zone_id": node["zone_id"],
            "floor": node["floor"],
            "bridge_name": node["bridge_name"],
            "latitude": node["latitude"],
            "longitude": node["longitude"],
            "sensors": {},
        })
        entry["sensors"][event["sensor_type"]] = event

    priorities = {event["priority"] for event in readings}
    priority = "critical" if "critical" in priorities else "high" if "high" in priorities else "normal"
    return {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "event_type": "telemetry_batch",
        "building_id": BUILDING_ID,
        "generated_at": now_utc(),
        "sequence_number": sequence,
        "priority": priority,
        "quality": "simulated_anomaly" if priority != "normal" else "valid",
        "delivery_policy": "immediate" if priority != "normal" else "periodic",
        "transport": "mqtt",
        "delivery_mode": "store_and_forward",
        "readings": list(by_node.values()),
    }


def save_batch_outbox(con: sqlite3.Connection, batch: dict[str, Any]) -> str:
    topic = EMERGENCY_TOPIC if batch["priority"] != "normal" else BATCH_TOPIC
    con.execute("""INSERT OR IGNORE INTO batch_outbox
        (batch_id, generated_at, sequence_number, priority, payload_json, topic)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (batch["event_id"], batch["generated_at"], batch["sequence_number"],
         batch["priority"], json.dumps(batch, ensure_ascii=False), topic))
    con.commit()
    return topic


def save_aggregate_outbox(con: sqlite3.Connection, aggregate: dict[str, Any]) -> None:
    con.execute("""INSERT OR IGNORE INTO aggregate_outbox
        (message_uid, generated_at, priority, payload_json)
        VALUES (?, ?, ?, ?)""", (
            aggregate["message_uid"], aggregate["generated_at"],
            aggregate["priority"], json.dumps(aggregate, ensure_ascii=False)))
    con.commit()


def publish_pending_api(con: sqlite3.Connection, api_url: str | None,
                        api_token: str | None, timeout: float,
                        only_uids: set[str] | None = None) -> int:
    """Envío por REST los paquetes nuevos que todavía están pendientes.

    Los paquetes antiguos quedan reservados para la recuperación por MQTT.
    """
    if not api_url:
        return 0
    sent = 0
    query = """SELECT message_uid, payload_json, attempts
        FROM aggregate_outbox WHERE status='pending'"""
    params: tuple[Any, ...] = ()
    if only_uids:
        placeholders = ",".join("?" for _ in only_uids)
        query += f" AND message_uid IN ({placeholders})"
        params = tuple(only_uids)
    query += " ORDER BY generated_at LIMIT 50"
    rows = con.execute(query, params).fetchall()
    for message_uid, payload_json, attempts in rows:
        payload = json.loads(payload_json)
        payload["delivery_status"] = "realtime"
        payload["transport"] = "rest"
        payload["sent_at"] = now_utc()
        endpoint = api_url.rstrip("/")
        endpoint += ("/api/v1/events/emergency" if payload.get("priority") != "normal"
                     else "/api/v1/telemetry/aggregate")
        headers = {"Content-Type": "application/json"}
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        request = urllib.request.Request(
            endpoint, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers, method="POST")
        body = ""
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                if 200 <= response.status < 300:
                    con.execute("""UPDATE aggregate_outbox
                        SET status='sent', attempts=attempts+1,
                        last_attempt_at=?, sent_at=?, response=?
                        WHERE message_uid=?""",
                                (now_utc(), now_utc(), body, message_uid))
                    con.commit()
                    sent += 1
                    continue
        except (OSError, urllib.error.HTTPError, urllib.error.URLError) as exc:
            body = str(exc)
        con.execute("""UPDATE aggregate_outbox
            SET attempts=attempts+1, last_attempt_at=?, response=?
            WHERE message_uid=?""", (now_utc(), body, message_uid))
        con.commit()
    return sent


def publish_pending_aggregate_mqtt(client: Any, con: sqlite3.Connection,
                                   enabled: bool) -> int:
    """Uso MQTT para recuperar los paquetes que no salieron por REST.

    Si REST ya confirmó un paquete, no lo vuelvo a enviar por MQTT.
    """
    if not enabled or client is None or not client.is_connected():
        return 0
    sent = 0
    rows = con.execute("""SELECT message_uid, payload_json, attempts
        FROM aggregate_outbox WHERE status='pending'
        ORDER BY generated_at LIMIT 50""").fetchall()
    topic = f"{TOPIC_ROOT}/{BUILDING_ID}/telemetry/aggregate"
    for message_uid, payload_json, attempts in rows:
        payload = json.loads(payload_json)
        payload["delivery_status"] = "catch_up" if int(attempts) > 0 else "realtime"
        payload["transport"] = "mqtt"
        payload["sent_at"] = now_utc()
        encoded = json.dumps(payload, ensure_ascii=False)
        result = client.publish(topic, encoded, qos=1, retain=False)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            con.execute("""UPDATE aggregate_outbox
                SET status='sent_mqtt', attempts=attempts+1,
                    last_attempt_at=?, sent_at=?, response=?
                WHERE message_uid=?""",
                        (now_utc(), payload["sent_at"], "mqtt:accepted", message_uid))
            con.commit()
            sent += 1
        else:
            con.execute("""UPDATE aggregate_outbox
                SET attempts=attempts+1, last_attempt_at=?, response=?
                WHERE message_uid=?""", (now_utc(), str(result.rc), message_uid))
            con.commit()
    return sent


def notify_brigadista_lora(aggregate: dict[str, Any], lora_enabled: bool,
                           lora_channel: VirtualRadioChannel) -> bool:
    """Mando un resumen corto al brigadista cuando no hay red.

    LoRa no reemplaza el envío al backend; solo permite avisar mientras la
    conexión principal está caída.
    """
    if not lora_enabled:
        return False
    emergency = aggregate.get("priority") in {"high", "critical"}
    delivered = True
    for bridge in aggregate.get("bridges", []):
        compact = {
            "schema_version": aggregate.get("schema_version", "1.0"),
            "message_uid": aggregate["message_uid"],
            "message_type": "emergency_event" if emergency else "telemetry_summary",
            "delivery_status": "emergency" if emergency else "offline_summary",
            "bridge_uid": bridge["node_uid"],
            "bridge_code": bridge.get("node_code"),
            "floor": bridge.get("floor"),
            "priority": aggregate.get("priority", "normal"),
            "generated_at": aggregate.get("generated_at"),
            "sequence_number": aggregate.get("sequence_number", 0),
            "sensors": [
                {
                    "sensor_uid": sensor.get("sensor_uid"),
                    "measurement_type": sensor.get("measurement_type"),
                    "data": sensor.get("data", {}),
                }
                for sensor in bridge.get("sensors", [])
            ],
        }
        result = lora_channel.transmit(json.dumps(compact, separators=(",", ":")))
        delivered = delivered and bool(result.success)
    return delivered


def pending_batch_rows(con: sqlite3.Connection) -> list[tuple[Any, ...]]:
    return con.execute("""SELECT batch_id, topic, payload_json, attempts
        FROM batch_outbox WHERE status='pending' ORDER BY generated_at LIMIT 50""").fetchall()


def mark_batch_published(con: sqlite3.Connection, batch_id: str) -> None:
    timestamp = now_utc()
    con.execute("""UPDATE batch_outbox SET status='published', attempts=attempts+1,
        last_attempt_at=?, published_at=? WHERE batch_id=?""",
                (timestamp, timestamp, batch_id))
    con.commit()


def mark_batch_attempt(con: sqlite3.Connection, batch_id: str) -> None:
    con.execute("UPDATE batch_outbox SET attempts=attempts+1, last_attempt_at=? WHERE batch_id=?",
                (now_utc(), batch_id))
    con.commit()


def publish_pending_batches(client: Any, con: sqlite3.Connection, enabled: bool,
                            bridge_state: dict[str, bool], lora_state: dict[str, bool],
                            mesh_state: bool, lora_channel: VirtualRadioChannel,
                            mesh_channel: VirtualRadioChannel) -> int:
    """Intento sacar un paquete de la cola y lo dejo guardado si no hay ruta.

    El radio virtual solo representa el acuse y la ruta de comunicación.
    """
    if not enabled or client is None or not client.is_connected():
        return 0
    sent = 0
    for batch_id, topic, payload, attempts in pending_batch_rows(con):
        batch = json.loads(payload)
        bridge_delivery: dict[str, Any] = {}
        routes_ok = True
        for node in batch.get("readings", []):
            node_id = node["node_id"]
            route = select_transport(node_id, bridge_state, lora_state, mesh_state)
            if route is None:
                routes_ok = False
                bridge_delivery[node_id] = {"status": "waiting_for_route", "ack_received": False}
                continue
            channel = lora_channel if route == "lora" else mesh_channel
            radio_result = channel.transmit(f"batch-route:{batch_id}:{node_id}")
            fallback_from = None
            if not radio_result.success and route == "lora" and mesh_state:
                fallback_from = route
                route = "ieee802154_mesh"
                radio_result = mesh_channel.transmit(f"batch-route:{batch_id}:{node_id}")
            bridge_delivery[node_id] = {
                "route": route,
                "status": "delivered" if radio_result.success else "failed",
                "ack_received": radio_result.ack_received,
                "latency_ms": radio_result.latency_ms,
                "reason": radio_result.reason,
            }
            if fallback_from:
                bridge_delivery[node_id]["fallback_from"] = fallback_from
            routes_ok = routes_ok and radio_result.success

        attempt = int(attempts) + 1
        if not routes_ok:
            batch["delivery_mode"] = "store_and_forward"
            batch["delivery"] = {"status": "waiting_for_route", "attempt": attempt,
                                  "bridges": bridge_delivery}
            con.execute("UPDATE batch_outbox SET payload_json=? WHERE batch_id=?",
                        (json.dumps(batch, ensure_ascii=False), batch_id))
            con.commit()
            mark_batch_attempt(con, batch_id)
            continue

        batch["delivery_mode"] = "live"
        batch["delivery"] = {"status": "delivered", "attempt": attempt,
                              "ack_received": True, "bridges": bridge_delivery}
        payload = json.dumps(batch, ensure_ascii=False)
        mqtt_result = client.publish(topic, payload, qos=1, retain=False)
        if mqtt_result.rc == mqtt.MQTT_ERR_SUCCESS:
            con.execute("UPDATE batch_outbox SET payload_json=? WHERE batch_id=?",
                        (payload, batch_id))
            con.commit()
            mark_batch_published(con, batch_id)
            sent += 1
        else:
            mark_batch_attempt(con, batch_id)
    return sent


def save_outbox(con: sqlite3.Connection, event: dict[str, Any]) -> str:
    sid = event["sensor_id"]
    topic = topic_for(event["node_id"], sid)
    con.execute("""INSERT OR IGNORE INTO outbox
        (event_id, sensor_id, node_id, sensor_type, generated_at, sequence_number,
         priority, quality, payload_json, topic)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (event["event_id"], sid, event["node_id"], event["sensor_type"],
         event["generated_at"], event["sequence_number"], event["priority"],
         event["quality"], json.dumps(event, ensure_ascii=False), topic))
    con.commit()
    return topic


def pending_rows(con: sqlite3.Connection) -> list[tuple[Any, ...]]:
    return con.execute("""SELECT event_id, topic, payload_json, attempts
        FROM outbox WHERE status='pending' ORDER BY generated_at LIMIT 100""").fetchall()


def mark_published(con: sqlite3.Connection, event_id: str) -> None:
    con.execute("""UPDATE outbox SET status='published', attempts=attempts+1,
        last_attempt_at=?, published_at=? WHERE event_id=?""", (now_utc(), now_utc(), event_id))
    con.commit()


def mark_attempt(con: sqlite3.Connection, event_id: str) -> None:
    con.execute("UPDATE outbox SET attempts=attempts+1, last_attempt_at=? WHERE event_id=?",
                (now_utc(), event_id))
    con.commit()


def update_delivery_metadata(event: dict[str, Any], route: str,
                             result: DeliveryResult | None, attempt: int,
                             fallback_from: str | None = None) -> str:
    event["transport"] = route
    event["delivery_mode"] = "live" if result and result.success else "store_and_forward"
    delivery: dict[str, Any] = {
        "attempt": attempt,
        "ack_received": bool(result and result.ack_received),
    }
    if result is not None:
        delivery.update({
            "status": "delivered" if result.success else "failed",
            "reason": result.reason,
            "latency_ms": result.latency_ms,
            "rssi_dbm": result.rssi_dbm,
            "snr_db": result.snr_db,
        })
    if fallback_from:
        delivery["fallback_from"] = fallback_from
    event["delivery"] = delivery
    return json.dumps(event, ensure_ascii=False)


def publish_pending(client: Any, con: sqlite3.Connection, enabled: bool,
                    bridge_state: dict[str, bool], lora_state: dict[str, bool],
                    mesh_state: bool, lora_channel: VirtualRadioChannel,
                    mesh_channel: VirtualRadioChannel) -> int:
    if not enabled or client is None or not client.is_connected():
        return 0
    sent = 0
    for event_id, topic, payload, _attempts in pending_rows(con):
        try:
            event = json.loads(payload)
            node_id = event["node_id"]
        except (json.JSONDecodeError, KeyError):
            node_id = ""
            event = None
        route = select_transport(node_id, bridge_state, lora_state, mesh_state)
        if event is None:
            continue

        attempt = int(_attempts) + 1
        if route is None:
            event["transport"] = "local_store"
            event["delivery_mode"] = "store_and_forward"
            event["delivery"] = {"status": "waiting_for_route", "ack_received": False}
            payload = json.dumps(event, ensure_ascii=False)
            con.execute("UPDATE outbox SET payload_json=? WHERE event_id=?", (payload, event_id))
            con.commit()
            continue

        first_route = route
        channel = lora_channel if route == "lora" else mesh_channel
        radio_result = channel.transmit(payload)
        fallback_from = None
        if not radio_result.success and route == "lora" and mesh_state:
            fallback_from = first_route
            route = "ieee802154_mesh"
            radio_result = mesh_channel.transmit(payload)

        payload = update_delivery_metadata(event, route, radio_result, attempt, fallback_from)
        con.execute("UPDATE outbox SET payload_json=? WHERE event_id=?", (payload, event_id))
        con.commit()

        if not radio_result.success:
            mark_attempt(con, event_id)
            continue

        mqtt_result = client.publish(topic, payload, qos=1, retain=False)
        if mqtt_result.rc == mqtt.MQTT_ERR_SUCCESS:
            mark_published(con, event_id)
            sent += 1
        else:
            mark_attempt(con, event_id)
    return sent


def print_status(con: sqlite3.Connection, mqtt_enabled: bool, anomalies: dict[str, set[str]]) -> None:
    total = con.execute("SELECT COUNT(*) FROM batch_outbox").fetchone()[0]
    pending = con.execute("SELECT COUNT(*) FROM batch_outbox WHERE status='pending'").fetchone()[0]
    published = con.execute("SELECT COUNT(*) FROM batch_outbox WHERE status='published'").fetchone()[0]
    print(f"status | mqtt_enabled={mqtt_enabled} | batches={total} | pending={pending} | published={published} | anomalies={anomalies}")


def command_loop(state: dict[str, Any], con: sqlite3.Connection, stop: threading.Event) -> None:
    print("Comandos: bridge1/bridge2 down|up, lora1/lora2 down|up, mesh down|up, mqtt down|up, anomaly, clear, status, quit")
    aliases = {"adxl355": "accelerometer", "grideye": "thermal_array",
               "bme688": "gas_environmental", "ina219": "power_monitor"}
    while not stop.is_set():
        try:
            parts = input("mqtt-sim> ").strip().lower().split()
        except (EOFError, KeyboardInterrupt):
            stop.set()
            return
        if not parts:
            continue
        with state["lock"]:
            if parts == ["quit"]:
                stop.set()
            elif parts == ["mqtt", "down"]:
                state["publish_enabled"] = False
                con.execute("INSERT INTO connectivity_log(observed_at,state,detail) VALUES (?,?,?)",
                            (now_utc(), "OFFLINE", "MQTT publication disabled by operator"))
                con.commit()
                print("MQTT -> OFFLINE; los eventos seguirán guardándose localmente")
            elif parts == ["mqtt", "up"]:
                state["publish_enabled"] = True
                print("MQTT -> ONLINE; se intentará publicar la cola pendiente")
            elif parts == ["status"]:
                print_status(con, state["publish_enabled"], state["anomalies"])
            elif len(parts) == 2 and parts[0] in {"bridge1", "bridge2"} and parts[1] in {"down", "up"}:
                node_id = "NODE-FLOOR-1" if parts[0] == "bridge1" else "NODE-FLOOR-2"
                state["bridges"][node_id] = parts[1] == "up"
                print(f"{parts[0].upper()} -> {'ONLINE' if state['bridges'][node_id] else 'OFFLINE'}")
            elif len(parts) == 2 and parts[0] in {"lora1", "lora2"} and parts[1] in {"down", "up"}:
                node_id = "NODE-FLOOR-1" if parts[0] == "lora1" else "NODE-FLOOR-2"
                state["lora"][node_id] = parts[1] == "up"
                print(f"{parts[0].upper()} -> {'ONLINE' if state['lora'][node_id] else 'OFFLINE'}")
            elif parts in (["mesh", "down"], ["mesh", "up"]):
                state["mesh"] = parts[1] == "up"
                print(f"MESH -> {'ONLINE' if state['mesh'] else 'OFFLINE'}")
            elif len(parts) == 3 and parts[0] in {"anomaly", "clear"}:
                node_id, sensor = parts[1].upper(), aliases.get(parts[2])
                if node_id in state["anomalies"] and sensor:
                    if parts[0] == "anomaly":
                        state["anomalies"][node_id].add(sensor)
                        # Despierto el productor para no esperar los 30 segundos.
                        # La emergencia sigue usando la misma cola y las mismas
                        # rutas de salida.
                        state["wake_event"].set()
                    else:
                        state["anomalies"][node_id].discard(sensor)
                    print(f"{parts[0]} -> {node_id} / {sensor}")
                else:
                    print("Nodo o sensor no reconocido")
            else:
                print("Comando no reconocido. Usa: status, mqtt down, mqtt up, anomaly, clear o quit")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sentinel Building MQTT sensor simulator")
    parser.add_argument("--host", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--mqtt-username", default=os.getenv("SENTINEL_MQTT_USERNAME"),
                        help="usuario MQTT; también puede definirse con SENTINEL_MQTT_USERNAME")
    parser.add_argument("--mqtt-password", default=os.getenv("SENTINEL_MQTT_PASSWORD"),
                        help="contraseña MQTT; también puede definirse con SENTINEL_MQTT_PASSWORD")
    parser.add_argument("--mqtt-tls", action="store_true",
                        help="activar TLS para el broker MQTT principal, normalmente puerto 8883")
    parser.add_argument("--mqtt-ca-file", default=os.getenv("SENTINEL_MQTT_CA_FILE"),
                        help="certificado CA PEM; también puede definirse con SENTINEL_MQTT_CA_FILE")
    parser.add_argument("--interval", type=float, default=30.0, help="seconds between normal telemetry cycles")
    parser.add_argument("--data-dir", default="data_mqtt", help="local SQLite directory")
    parser.add_argument("--dry-run", action="store_true", help="generate and store without MQTT")
    parser.add_argument("--lora-loss-rate", type=float, default=0.10,
                        help="probabilidad de pérdida del enlace LoRa (0-1)")
    parser.add_argument("--lora-min-delay-ms", type=int, default=100,
                        help="latencia mínima virtual de LoRa")
    parser.add_argument("--lora-max-delay-ms", type=int, default=400,
                        help="latencia máxima virtual de LoRa")
    parser.add_argument("--lora-max-payload-bytes", type=int, default=1200,
                        help="tamaño máximo del payload LoRa simulado (demo JSON completo)")
    parser.add_argument("--lora-seed", type=int, default=None,
                        help="semilla opcional para repetir el escenario")
    parser.add_argument("--status-file", default="data_mqtt/runtime_status.json",
                        help="archivo JSON con el estado para el panel visual")
    parser.add_argument("--api-url", default=os.getenv("SENTINEL_API_URL"),
                        help="URL base de la caja negra FastAPI")
    parser.add_argument("--api-token", default=os.getenv("SENTINEL_API_TOKEN"),
                        help="token Bearer opcional para la API REST")
    parser.add_argument("--api-timeout", type=float, default=10.0,
                        help="timeout en segundos para la API REST")
    parser.add_argument("--bridge-url", default=os.getenv("SENTINEL_BRIDGE_URL"),
                        help="URL local del bridge simulado; activa el modo sensor-only")
    args = parser.parse_args()
    sensor_only = bool(args.bridge_url)
    if not sensor_only and not args.dry_run and mqtt is None:
        raise SystemExit("Falta paho-mqtt. Ejecuta: python -m pip install paho-mqtt")

    data_dir = Path(args.data_dir)
    con = open_store(data_dir / "bridge_outbox.db")
    register_catalog(con)
    state = {"publish_enabled": not args.dry_run,
             "anomalies": {node_id: set() for node_id in NODES},
             "bridges": {node_id: True for node_id in NODES},
             "lora": {node_id: True for node_id in NODES},
             "mesh": True,
             "wake_event": threading.Event(),
             "lock": threading.Lock()}
    stop = threading.Event()
    threading.Thread(target=command_loop, args=(state, con, stop), daemon=True).start()

    client = None
    lora_channel = VirtualRadioChannel(
        name="lora", loss_rate=args.lora_loss_rate,
        min_delay_ms=args.lora_min_delay_ms,
        max_delay_ms=args.lora_max_delay_ms,
        max_payload_bytes=args.lora_max_payload_bytes,
        seed=args.lora_seed,
    )
    mesh_channel = VirtualRadioChannel(
        name="ieee802154_mesh", loss_rate=0.02,
        min_delay_ms=20, max_delay_ms=100,
        max_payload_bytes=1024,
        seed=None if args.lora_seed is None else args.lora_seed + 1,
    )
    if not sensor_only and not args.dry_run:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sentinel-simulator")
        client.reconnect_delay_set(min_delay=1, max_delay=15)
        try:
            if args.mqtt_username is not None:
                client.username_pw_set(args.mqtt_username, args.mqtt_password or "")
            if args.mqtt_tls:
                client.tls_set(ca_certs=args.mqtt_ca_file, cert_reqs=ssl.CERT_REQUIRED)
            client.connect(args.host, args.port, keepalive=30)
            client.loop_start()
        except OSError as exc:
            print(f"No se pudo conectar a MQTT ({exc}); se continuará en modo local")
            state["publish_enabled"] = False

    print(f"Simulador iniciado | building={BUILDING_ID} | intervalo_normal={args.interval}s | "
          f"emergencias=inmediatas | modo={'sensor-only' if sensor_only else 'legacy'} | data={data_dir}")
    sequence = 0
    try:
        while not stop.is_set():
            sequence += 1
            with state["lock"]:
                active = {node: values.copy() for node, values in state["anomalies"].items()}
                enabled = state["publish_enabled"]
                bridge_state = dict(state["bridges"])
                lora_state = dict(state["lora"])
                mesh_state = state["mesh"]
            all_readings: list[dict[str, Any]] = []
            for node_id in NODES:
                for event in readings_for(node_id, sequence, active[node_id]):
                    all_readings.append(event)
            if sensor_only:
                endpoint = args.bridge_url.rstrip("/") + "/v1/readings"
                request = urllib.request.Request(
                    endpoint,
                    data=json.dumps({"readings": all_readings}, ensure_ascii=False).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(request, timeout=args.api_timeout) as response:
                        result = json.loads(response.read().decode("utf-8"))
                    print(f"cycle={sequence:05d} | generated={len(all_readings):02d} readings | "
                          f"bridge_inserted={result.get('raw_inserted', 0):02d} | "
                          f"rest={result.get('rest_realtime', False)} | "
                          f"mqtt_catchup={result.get('mqtt_catch_up', 0):02d} | "
                          f"lora={'ON' if result.get('lora_summary') else 'OFF'}")
                except (OSError, urllib.error.HTTPError, urllib.error.URLError,
                        json.JSONDecodeError) as exc:
                    print(f"cycle={sequence:05d} | bridge_unavailable={exc}")
                state["wake_event"].wait(args.interval)
                state["wake_event"].clear()
                continue
            batch = batch_envelope(all_readings, sequence)
            save_batch_outbox(con, batch)
            aggregate = aggregate_readings(
                all_readings, BUILDING_ID, args.interval, sequence, NODES)
            save_aggregate_outbox(con, aggregate)
            # REST lleva los datos nuevos y MQTT queda para recuperar lo pendiente.
            api_published = publish_pending_api(
                con, args.api_url, args.api_token, args.api_timeout,
                only_uids={aggregate["message_uid"]})
            mqtt_recovered = publish_pending_aggregate_mqtt(client, con, enabled)
            mqtt_online = bool(enabled and client is not None and client.is_connected())
            network_online = mqtt_online or api_published > 0
            lora_summary = notify_brigadista_lora(
                aggregate,
                (not network_online) and (
                    lora_state.get("NODE-FLOOR-1", False)
                    or lora_state.get("NODE-FLOOR-2", False)
                ),
                lora_channel)
            pending = con.execute("SELECT COUNT(*) FROM batch_outbox WHERE status='pending'").fetchone()[0]
            status_path = Path(args.status_file)
            status_path.parent.mkdir(parents=True, exist_ok=True)
            status_path.write_text(json.dumps({
                "cycle": sequence,
                "normal_interval_s": args.interval,
                "emergency_dispatch": "immediate",
                "mqtt": "ONLINE" if enabled else "OFFLINE",
                "mqtt_recovered": mqtt_recovered,
                "lora_brigadista_summary": lora_summary,
                "fastapi": "ONLINE" if args.api_url else "DISABLED",
                "mesh": "ONLINE" if mesh_state else "OFFLINE",
                "bridges": {
                    node: {
                        "status": "ONLINE" if bridge_state[node] else "OFFLINE",
                        "lora": "ONLINE" if lora_state[node] else "OFFLINE",
                        "route": select_transport(node, bridge_state, lora_state, mesh_state) or "local_store",
                        "anomalies": sorted(active[node]),
                    } for node in NODES
                },
                "pending": pending,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            api_pending = con.execute(
                "SELECT COUNT(*) FROM aggregate_outbox WHERE status='pending'"
            ).fetchone()[0]
            print(f"cycle={sequence:05d} | generated={len(all_readings):02d} readings | rest_realtime={api_published:02d} | mqtt_catchup={mqtt_recovered:02d} | pending_api={api_pending:04d} | lora_summary={'ON' if lora_summary else 'OFF'} | mqtt={'ON' if enabled else 'OFF'}")
            # En un ciclo normal espero el intervalo. El comando de emergencia
            # despierta este hilo para enviar la lectura de inmediato.
            state["wake_event"].wait(args.interval)
            state["wake_event"].clear()
    except KeyboardInterrupt:
        stop.set()
    finally:
        if client is not None:
            client.loop_stop()
            client.disconnect()
        con.close()
        print("Simulador detenido; la outbox local permanece en la base SQLite.")


if __name__ == "__main__":
    main()

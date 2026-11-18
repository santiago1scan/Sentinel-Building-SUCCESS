from __future__ import annotations

import hashlib
import hmac
import struct
import time
import uuid
from dataclasses import dataclass

MAGIC = b"SB"
VERSION = 1
ALERT, RADIO_ACK, HUMAN_ACK, HEARTBEAT = 1, 2, 3, 4
FRAME = struct.Struct("!2sBB16sBBBBIIhhH")
AUTH_BYTES = 8
MAX_FRAME_BYTES = 64

SENSORS = {"ADXL355": 1, "AMG8833": 2, "BME688": 3, "INA219": 4}
SENSOR_NAMES = {value: key for key, value in SENSORS.items()}
EVENTS = {"VIBRATION_HIGH": 1, "HOTSPOT": 2, "AIR_QUALITY": 3, "POWER_LOW": 4}
EVENT_NAMES = {value: key for key, value in EVENTS.items()}


@dataclass(frozen=True)
class LoRaFrame:
    frame_type: int
    message_uid: str
    node: int
    sensor: int
    event: int
    sequence: int
    timestamp: int
    value_scaled: int
    threshold_scaled: int
    battery_mv: int


def encode(frame: LoRaFrame, key: bytes) -> bytes:
    body = FRAME.pack(
        MAGIC,
        VERSION,
        frame.frame_type,
        uuid.UUID(frame.message_uid).bytes,
        frame.node,
        frame.sensor,
        frame.event,
        0,
        frame.sequence,
        frame.timestamp,
        frame.value_scaled,
        frame.threshold_scaled,
        frame.battery_mv,
    )
    tag = hmac.new(key, body, hashlib.sha256).digest()[:AUTH_BYTES]
    packet = body + tag
    if len(packet) > MAX_FRAME_BYTES:
        raise ValueError("La trama supera el límite conservador de 64 bytes")
    return packet


def decode(packet: bytes, key: bytes) -> LoRaFrame:
    if len(packet) != FRAME.size + AUTH_BYTES:
        raise ValueError("Tamaño de trama inválido")
    body, received_tag = packet[:-AUTH_BYTES], packet[-AUTH_BYTES:]
    expected_tag = hmac.new(key, body, hashlib.sha256).digest()[:AUTH_BYTES]
    if not hmac.compare_digest(received_tag, expected_tag):
        raise ValueError("Autenticación HMAC inválida")
    magic, version, kind, uid, node, sensor, event, _, seq, stamp, value, limit, battery = FRAME.unpack(body)
    if magic != MAGIC or version != VERSION:
        raise ValueError("Protocolo LoRa no compatible")
    return LoRaFrame(kind, str(uuid.UUID(bytes=uid)), node, sensor, event, seq, stamp, value, limit, battery)


def acknowledgment(original: LoRaFrame, kind: int) -> LoRaFrame:
    return LoRaFrame(kind, original.message_uid, original.node, original.sensor, original.event,
                     original.sequence, int(time.time()), original.value_scaled,
                     original.threshold_scaled, original.battery_mv)

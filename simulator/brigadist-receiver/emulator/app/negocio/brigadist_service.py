from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from app.core.lora_protocol import (
    ALERT, EVENT_NAMES, HUMAN_ACK, RADIO_ACK, SENSOR_NAMES,
    acknowledgment, decode, encode,
)
from app.core.time_utils import utc_now
from app.datos.canales.lora_channel import LoRaReceiverChannel
from app.datos.repositorios.local_history import LocalHistory


class BrigadistService:
    """Autentica, muestra y confirma alertas; no conoce el bridge interno."""

    def __init__(self, host: str, port: int, key: bytes, history: Path) -> None:
        self.key = key
        self.history = LocalHistory(history)
        self.alerts: dict[str, dict[str, Any]] = {}
        self.sources: dict[str, tuple[str, int]] = {}
        self.frames: dict[str, Any] = {}
        self.lock = threading.RLock()
        self.invalid_frames = 0
        self.channel = LoRaReceiverChannel(host, port, self._receive)

    def _receive(self, packet: bytes, source: tuple[str, int]) -> bytes | None:
        try:
            frame = decode(packet, self.key)
        except ValueError:
            self.invalid_frames += 1
            return None
        if frame.frame_type != ALERT:
            return None
        with self.lock:
            if frame.message_uid not in self.alerts:
                self.alerts[frame.message_uid] = {
                    "message_uid": frame.message_uid, "node": frame.node,
                    "sensor": SENSOR_NAMES.get(frame.sensor, "UNKNOWN"),
                    "event": EVENT_NAMES.get(frame.event, "UNKNOWN"),
                    "value_scaled": frame.value_scaled,
                    "threshold_scaled": frame.threshold_scaled,
                    "battery_mv": frame.battery_mv, "received_at": utc_now(),
                    "radio_status": "RADIO_RECEIVED", "human_status": "WAITING",
                }
            self.sources[frame.message_uid] = source
            self.frames[frame.message_uid] = frame
            self._persist()
        return encode(acknowledgment(frame, RADIO_ACK), self.key)

    def acknowledge(self, uid: str) -> bool:
        with self.lock:
            if uid not in self.alerts:
                return False
            self.alerts[uid]["human_status"] = "HUMAN_ACKNOWLEDGED"
            self.alerts[uid]["acknowledged_at"] = utc_now()
            packet = encode(acknowledgment(self.frames[uid], HUMAN_ACK), self.key)
            self.channel.send(packet, self.sources[uid])
            self._persist()
            return True

    def snapshot(self) -> list[dict[str, Any]]:
        with self.lock:
            return sorted(self.alerts.values(), key=lambda item: item["received_at"], reverse=True)

    def _persist(self) -> None:
        self.history.save(self.snapshot())

    def close(self) -> None:
        self.channel.close()

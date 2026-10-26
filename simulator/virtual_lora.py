"""Canales de radio virtuales para la simulación de Sentinel Building."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveryResult:
    success: bool
    reason: str
    latency_ms: int
    rssi_dbm: int
    snr_db: float
    ack_received: bool


class VirtualRadioChannel:
    """Simula latencia, pérdida, tamaño máximo y confirmación de un enlace."""

    def __init__(self, *, name: str, loss_rate: float,
                 min_delay_ms: int, max_delay_ms: int,
                 max_payload_bytes: int, seed: int | None = None) -> None:
        if not 0 <= loss_rate <= 1:
            raise ValueError("loss_rate debe estar entre 0 y 1")
        if min_delay_ms < 0 or max_delay_ms < min_delay_ms:
            raise ValueError("rango de latencia inválido")
        self.name = name
        self.loss_rate = loss_rate
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms
        self.max_payload_bytes = max_payload_bytes
        self.random = random.Random(seed)

    def transmit(self, payload: str) -> DeliveryResult:
        payload_bytes = len(payload.encode("utf-8"))
        latency = self.random.randint(self.min_delay_ms, self.max_delay_ms)
        rssi = self.random.randint(-112, -72)
        snr = round(self.random.uniform(-10.0, 9.0), 1)
        time.sleep(latency / 1000)

        if payload_bytes > self.max_payload_bytes:
            return DeliveryResult(False, "payload_too_large", latency, rssi, snr, False)
        if self.random.random() < self.loss_rate:
            return DeliveryResult(False, "packet_lost", latency, rssi, snr, False)
        return DeliveryResult(True, "ack_received", latency, rssi, snr, True)

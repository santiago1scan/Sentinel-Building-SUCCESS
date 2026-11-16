"""Adaptador del canal LoRa virtual: transmite solo el resumen del agregado."""

import json
from dataclasses import dataclass
from typing import Any

from app.datos.canales.virtual_lora import VirtualRadioChannel


@dataclass(frozen=True)
class ResultadoLora:
    success: bool
    reason: str
    latency_ms: int


class LoraCanal:
    def __init__(self, *, loss_rate: float, min_delay_ms: int, max_delay_ms: int,
                 max_payload_bytes: int, seed: int | None = None) -> None:
        self._canal = VirtualRadioChannel(
            name="lora", loss_rate=loss_rate,
            min_delay_ms=min_delay_ms, max_delay_ms=max_delay_ms,
            max_payload_bytes=max_payload_bytes, seed=seed,
        )

    def transmitir_resumen(self, resumen: dict[str, Any]) -> ResultadoLora:
        texto = json.dumps(resumen, separators=(",", ":"))
        resultado = self._canal.transmit(texto)
        return ResultadoLora(resultado.success, resultado.reason, resultado.latency_ms)

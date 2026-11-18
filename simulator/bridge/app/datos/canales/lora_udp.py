from __future__ import annotations

import random
import socket
import threading
import time
from collections.abc import Callable

from app.core.lora_protocol import HUMAN_ACK, RADIO_ACK, LoRaFrame, decode, encode


class VirtualSX1262:
    """Simula el enlace físico SX1262 sin mezclarlo con SQLite ni REST."""

    def __init__(self, node: int, receiver_host: str, receiver_port: int, key: bytes,
                 on_ack: Callable[[str, str], None], loss_rate: float = 0.0) -> None:
        self.node = node
        self.destination = (receiver_host, receiver_port)
        self.key = key
        self.on_ack = on_ack
        self.loss_rate = loss_rate
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("0.0.0.0", 0))
        self.socket.settimeout(0.5)
        self.running = True
        threading.Thread(target=self._listen, daemon=True).start()

    def transmit(self, frame: LoRaFrame) -> dict[str, float | int | str]:
        packet = encode(frame, self.key)
        latency_ms = random.randint(80, 240)
        time.sleep(latency_ms / 1000)
        dropped = random.random() < self.loss_rate
        if not dropped:
            self.socket.sendto(packet, self.destination)
        return {
            "bytes": len(packet),
            "latency_ms": latency_ms,
            "rssi_dbm": round(random.uniform(-105, -72), 1),
            "snr_db": round(random.uniform(2.0, 9.0), 1),
            "result": "DROPPED" if dropped else "TRANSMITTED",
        }

    def _listen(self) -> None:
        while self.running:
            try:
                packet, _ = self.socket.recvfrom(128)
                frame = decode(packet, self.key)
                if frame.frame_type == RADIO_ACK:
                    self.on_ack(frame.message_uid, "RADIO_RECEIVED")
                elif frame.frame_type == HUMAN_ACK:
                    self.on_ack(frame.message_uid, "HUMAN_ACKNOWLEDGED")
            except socket.timeout:
                continue
            except (OSError, ValueError):
                continue

    def close(self) -> None:
        self.running = False
        self.socket.close()

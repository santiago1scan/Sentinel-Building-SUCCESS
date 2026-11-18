from __future__ import annotations

import socket
import threading
from collections.abc import Callable


class LoRaReceiverChannel:
    """UDP en la Beta; SX1262 físico en el Heltec final."""

    def __init__(self, host: str, port: int,
                 on_packet: Callable[[bytes, tuple[str, int]], bytes | None]) -> None:
        self.on_packet = on_packet
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((host, port))
        self.running = True
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self) -> None:
        while self.running:
            try:
                packet, source = self.socket.recvfrom(128)
                response = self.on_packet(packet, source)
                if response:
                    self.socket.sendto(response, source)
            except OSError:
                if self.running:
                    continue

    def send(self, packet: bytes, destination: tuple[str, int]) -> None:
        self.socket.sendto(packet, destination)

    def close(self) -> None:
        self.running = False
        self.socket.close()

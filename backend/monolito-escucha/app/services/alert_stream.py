"""Stream de alertas (Server-Sent Events) para el panel.

El broadcaster vive en memoria de este proceso: cada cliente conectado tiene una cola y cada
evento se copia a todas. Con una sola réplica de escucha basta; con varias, cada réplica solo
avisaría a sus propios clientes.
"""
import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

KEEPALIVE_SECONDS = 15
QUEUE_SIZE = 256
_CLOSE = object()


class AlertBroadcaster:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    def publish(self, event: str, data: dict[str, Any]) -> None:
        for queue in list(self._subscribers):
            try:
                queue.put_nowait((event, data))
            except asyncio.QueueFull:
                # Cliente que no consume: se corta para no acumular memoria. El frontend reconecta.
                self._subscribers.discard(queue)
                _drain_and_close(queue)


def _drain_and_close(queue: asyncio.Queue) -> None:
    while True:
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            break
    queue.put_nowait(_CLOSE)


def format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str, ensure_ascii=False)}\n\n"


SnapshotFn = Callable[[], Awaitable[list[dict[str, Any]]]]


async def alert_event_stream(
    broadcaster: AlertBroadcaster,
    snapshot: SnapshotFn | None = None,
    keepalive_seconds: float = KEEPALIVE_SECONDS,
) -> AsyncIterator[str]:
    """Genera el cuerpo del stream.

    Primero se suscribe, para no perder cambios mientras se lee el estado actual. Después envía el
    snapshot (alertas visibles) como eventos `alert`, marca el final con `alerts_ready` y sigue con los
    cambios en vivo. Un comentario de keepalive cada `keepalive_seconds` mantiene la conexión.
    """
    queue = broadcaster.subscribe()
    try:
        if snapshot is not None:
            for data in await snapshot():
                yield format_sse("alert", data)
            yield format_sse("alerts_ready", {})
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=keepalive_seconds)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue
            if item is _CLOSE:
                return
            event, data = item
            yield format_sse(event, data)
    finally:
        broadcaster.unsubscribe(queue)


alert_broadcaster = AlertBroadcaster()

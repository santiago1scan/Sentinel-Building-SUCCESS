"""Stream de alertas: broadcaster, formato SSE y payload que recibe el frontend."""
import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.alert_events import alert_payload
from app.services.alert_stream import AlertBroadcaster, alert_event_stream, format_sse


def test_format_sse_produce_evento_y_datos_en_json():
    text = format_sse("alert", {"alert_id": 7, "alert_type": "out_of_range"})
    assert text.startswith("event: alert\ndata: ")
    assert text.endswith("\n\n")
    payload = json.loads(text.split("data: ", 1)[1].strip())
    assert payload == {"alert_id": 7, "alert_type": "out_of_range"}


@pytest.mark.asyncio
async def test_publish_llega_a_todos_los_suscriptores():
    broadcaster = AlertBroadcaster()
    first = broadcaster.subscribe()
    second = broadcaster.subscribe()

    broadcaster.publish("alert_resolved", {"alert_id": 3})

    assert first.get_nowait() == ("alert_resolved", {"alert_id": 3})
    assert second.get_nowait() == ("alert_resolved", {"alert_id": 3})


@pytest.mark.asyncio
async def test_cliente_lento_se_desconecta_y_su_stream_termina():
    broadcaster = AlertBroadcaster()
    chunks = alert_event_stream(broadcaster, keepalive_seconds=60)
    consumer = asyncio.create_task(_collect(chunks))
    await asyncio.sleep(0)  # deja que el stream se suscriba
    assert broadcaster.subscriber_count == 1

    # Llena la cola sin consumirla hasta desbordarla.
    from app.services.alert_stream import QUEUE_SIZE

    for i in range(QUEUE_SIZE + 1):
        broadcaster.publish("alert", {"alert_id": i})

    assert broadcaster.subscriber_count == 0
    await asyncio.wait_for(consumer, timeout=2)


async def _collect(stream):
    return [chunk async for chunk in stream]


@pytest.mark.asyncio
async def test_stream_envia_eventos_y_keepalive_y_se_da_de_baja():
    broadcaster = AlertBroadcaster()
    stream = alert_event_stream(broadcaster, keepalive_seconds=0.01)

    first = asyncio.create_task(stream.__anext__())
    await asyncio.sleep(0.05)
    assert first.done() and await first == ": keepalive\n\n"

    nxt = asyncio.create_task(stream.__anext__())
    await asyncio.sleep(0)
    broadcaster.publish("alert", {"alert_id": 1})
    assert await asyncio.wait_for(nxt, timeout=1) == format_sse("alert", {"alert_id": 1})

    await stream.aclose()
    assert broadcaster.subscriber_count == 0


def test_alert_payload_incluye_lo_que_necesita_el_panel():
    at = datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc)
    alert = SimpleNamespace(
        alert_id=5, event_uuid="u-1", alert_type="out_of_range", alert_code="OUT_OF_RANGE_ABOVE",
        direction="above", node_id=2, sensor_id=9, metric_id=4, started_at=at, last_seen_at=at,
        ended_at=None, handled_by_user_id=None, handled_at=None, severity="leve",
    )

    payload = alert_payload(alert)

    assert payload["alert_id"] == 5
    assert payload["node_id"] == 2
    assert payload["alert_type"] == "out_of_range"
    assert payload["started_at"] == "2026-11-16T10:00:00+00:00"
    assert payload["visible"] is True
    assert payload["severity"] == "leve"


@pytest.mark.asyncio
async def test_snapshot_va_primero_luego_alerts_ready_y_despues_cambios_en_vivo():
    broadcaster = AlertBroadcaster()

    async def snapshot():
        # Mientras se lee el estado, llega un cambio en vivo: debe quedar en cola, no perderse.
        broadcaster.publish("alert", {"alert_id": 99})
        return [{"alert_id": 1}, {"alert_id": 2}]

    stream = alert_event_stream(broadcaster, snapshot=snapshot, keepalive_seconds=60)
    chunks = [await stream.__anext__() for _ in range(4)]

    assert chunks == [
        format_sse("alert", {"alert_id": 1}),
        format_sse("alert", {"alert_id": 2}),
        format_sse("alerts_ready", {}),
        format_sse("alert", {"alert_id": 99}),
    ]
    await stream.aclose()
    assert broadcaster.subscriber_count == 0


@pytest.mark.asyncio
async def test_sin_snapshot_no_se_envia_alerts_ready():
    broadcaster = AlertBroadcaster()
    stream = alert_event_stream(broadcaster, keepalive_seconds=60)
    nxt = asyncio.create_task(stream.__anext__())
    await asyncio.sleep(0)
    broadcaster.publish("alert", {"alert_id": 5})

    assert await asyncio.wait_for(nxt, timeout=1) == format_sse("alert", {"alert_id": 5})
    await stream.aclose()

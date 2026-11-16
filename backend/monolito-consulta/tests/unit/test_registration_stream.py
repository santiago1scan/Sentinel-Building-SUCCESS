"""Stream SSE de solicitudes pendientes: emite al conectar y en cada cambio."""
import asyncio
import json

import pytest

from app.api.routes.registrations import _pending_events, format_sse
from app.services.registration_store import RegistrationStore


def test_format_sse_produces_named_event_with_json_data():
    text = format_sse("pending", [{"code": "NODE-X"}])

    assert text == 'event: pending\ndata: [{"code": "NODE-X"}]\n\n'
    assert json.loads(text.split("data: ", 1)[1].strip()) == [{"code": "NODE-X"}]


@pytest.mark.asyncio
async def test_stream_sends_current_list_on_connect_and_again_on_change():
    store = RegistrationStore(ttl_seconds=300)
    events = _pending_events(store)

    first = await asyncio.wait_for(events.__anext__(), 3)
    assert first.startswith("event: pending")
    assert json.loads(first.split("data: ", 1)[1].strip()) == []

    store.create("NODE-X", "Bridge X", "SB-001", "ZONE-X")

    second = await asyncio.wait_for(events.__anext__(), 3)
    payload = json.loads(second.split("data: ", 1)[1].strip())
    assert [p["code"] for p in payload] == ["NODE-X"]
    assert payload[0]["status"] == "pending"
    await events.aclose()


def test_store_version_grows_with_each_change():
    store = RegistrationStore(ttl_seconds=300)
    before = store.version

    store.create("NODE-Y", "Bridge Y", "SB-001", "ZONE-Y")

    assert store.version > before

"""Marcar como atendida: cambia el estado y nunca borra la fila."""
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.alert import Alert
from app.services.alert_handling import mark_alert_handled


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Alert.__table__.create)
    now = datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add(Alert(
            alert_id=1, event_uuid="u-1", alert_type="technical", alert_code="NODE_SILENT", node_id=2,
            started_at=now, last_seen_at=now, generated_at=now, reading_count=0,
        ))
        await session.commit()
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_marca_atendida_sin_borrar(session):
    alert = await mark_alert_handled(session, 1, user_id=5)

    assert alert.handled_by_user_id == 5
    assert alert.handled_at is not None
    rows = (await session.execute(select(Alert))).scalars().all()
    assert len(rows) == 1
    assert rows[0].ended_at is None  # atender no cierra el evento: eso lo decide el dato normal


@pytest.mark.asyncio
async def test_alerta_inexistente_devuelve_none(session):
    assert await mark_alert_handled(session, 999, user_id=5) is None

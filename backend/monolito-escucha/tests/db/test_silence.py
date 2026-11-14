"""A node that stops sending its half-hour summary opens NODE_SILENT; its next message closes it."""
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.analytics.silence_monitor import check_silent_nodes
from app.models import Alert
from tests.db.test_ingest import T0, count, ingest, session, summary  # noqa: F401  (fixture)

pytestmark = pytest.mark.asyncio


async def test_node_without_summary_for_36_minutes_opens_node_silent_once(session):  # noqa: F811
    await ingest(session, summary("s-1", T0))

    assert await check_silent_nodes(session, now=T0 + timedelta(minutes=34), threshold_minutes=35) == 0
    assert await check_silent_nodes(session, now=T0 + timedelta(minutes=36), threshold_minutes=35) == 1
    await check_silent_nodes(session, now=T0 + timedelta(minutes=41), threshold_minutes=35)
    await session.commit()

    alert = (await session.execute(select(Alert).where(Alert.alert_code == "NODE_SILENT"))).scalar_one()
    assert alert.alert_type == "technical" and alert.ended_at is None

    await ingest(session, summary("s-2", T0 + timedelta(minutes=50)))
    await session.refresh(alert)
    assert alert.ended_at == T0 + timedelta(minutes=50)


async def test_node_never_heard_is_not_reported(session):  # noqa: F811
    assert await check_silent_nodes(session, now=T0, threshold_minutes=35) == 0
    assert await count(session, Alert) == 0

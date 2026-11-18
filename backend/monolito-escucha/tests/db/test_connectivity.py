"""The panel shows a node as connected while it has an open connectivity_log session."""
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.analytics.silence_monitor import check_silent_nodes
from app.models import ConnectivityLog, Node
from tests.db.test_ingest import T0, count, ingest, session, summary  # noqa: F401  (fixture)

pytestmark = pytest.mark.asyncio


async def sessions(session):  # noqa: F811
    return (await session.execute(select(ConnectivityLog).order_by(ConnectivityLog.connectivity_id))).scalars().all()


async def test_first_message_opens_one_session_and_the_next_ones_reuse_it(session):  # noqa: F811
    await ingest(session, summary("s-1", T0))
    await ingest(session, summary("s-2", T0 + timedelta(minutes=30)))

    (opened,) = await sessions(session)
    assert opened.started_at == T0 and opened.ended_at is None


async def test_duplicate_message_does_not_open_a_session(session):  # noqa: F811
    await ingest(session, summary("s-1", T0))
    await ingest(session, summary("s-1", T0))
    assert await count(session, ConnectivityLog) == 1


async def test_silent_node_closes_its_session_at_the_last_signal_and_reopens_on_return(session):  # noqa: F811
    last = T0 + timedelta(minutes=30)
    await ingest(session, summary("s-1", T0))
    await ingest(session, summary("s-2", last))

    await check_silent_nodes(session, now=last + timedelta(minutes=34), threshold_minutes=35)
    assert (await sessions(session))[0].ended_at is None  # still within the threshold

    await check_silent_nodes(session, now=last + timedelta(minutes=36), threshold_minutes=35)
    (closed,) = await sessions(session)
    assert closed.ended_at == last

    await ingest(session, summary("s-3", last + timedelta(minutes=50)))
    closed, reopened = await sessions(session)
    assert reopened.started_at == last + timedelta(minutes=50) and reopened.ended_at is None


async def test_revoked_node_does_not_stay_connected(session):  # noqa: F811
    await ingest(session, summary("s-1", T0))
    node = (await session.execute(select(Node))).scalar_one()
    node.revoked_at = T0 + timedelta(minutes=1)
    await session.flush()

    await check_silent_nodes(session, now=T0 + timedelta(minutes=2), threshold_minutes=35)
    (log,) = await sessions(session)
    assert log.ended_at == T0

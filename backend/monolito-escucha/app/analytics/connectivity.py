"""Connectivity sessions of a node: the panel shows "Conectado" while one is open (ended_at IS NULL).

Nothing else writes connectivity_log during ingest, so this is what makes a node that is sending data show as
connected:

- A message from the node opens a session if it has none open (`open_session`, called during ingest).
- A node silent for longer than the threshold, or revoked, gets its open session closed at the time of its last
  signal (`close_silent_sessions`, called by the silence monitor). It is the same threshold as NODE_SILENT, so
  "disconnected" and the technical alert always agree.

Time is the server's arrival time (node.last_signal_received_at), never the bridge clock.
"""
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connectivity_log import ConnectivityLog
from app.models.node import Node


async def open_session(session: AsyncSession, node_id: int, at: datetime) -> bool:
    """Open a session unless the node already has one. Returns True if it opened one. No commit."""
    # Two messages of the same node arriving together must not both open a session: serialize on the node row.
    await session.execute(select(Node.node_id).where(Node.node_id == node_id).with_for_update())
    active = (await session.execute(select(ConnectivityLog.connectivity_id).where(
        ConnectivityLog.node_id == node_id, ConnectivityLog.ended_at.is_(None)).limit(1))).first()
    if active is not None:
        return False
    session.add(ConnectivityLog(node_id=node_id, started_at=at))
    await session.flush()
    return True


async def close_silent_sessions(session: AsyncSession, *, now: datetime, threshold_minutes: int) -> int:
    """Close the open session of every node silent for longer than the threshold or revoked. No commit."""
    limit = now - timedelta(minutes=threshold_minutes)
    rows = (await session.execute(
        select(ConnectivityLog, Node).join(Node, Node.node_id == ConnectivityLog.node_id).where(
            ConnectivityLog.ended_at.is_(None),
            or_(Node.revoked_at.is_not(None), Node.last_signal_received_at < limit),
        ))).all()
    for log, node in rows:
        # The session ended when the node was last heard (never before it started: chk_connectivity_log_dates).
        log.ended_at = max(log.started_at, node.last_signal_received_at or log.started_at)
    await session.flush()
    return len(rows)

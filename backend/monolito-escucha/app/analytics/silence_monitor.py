"""Nodes that stop sending. A node whose last message is older than the threshold gets NODE_SILENT.

The bridge sends a summary every 30 minutes, so the default threshold is 35 minutes (one summary plus margin).
The alert closes on the node's next message (AlertEngine.on_node_heard, called during ingest).
The same check closes the node's connectivity session (app/analytics/connectivity.py).
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.analytics.alert_engine import AlertEngine
from app.analytics.connectivity import close_silent_sessions
from app.models.node import Node
from app.repositories.analytics_repositories import AlertRepository

logger = logging.getLogger(__name__)


async def check_silent_nodes(session: AsyncSession, *, now: datetime, threshold_minutes: int) -> int:
    """Open (or keep open) NODE_SILENT for every silent node. Returns how many nodes are silent. No commit."""
    limit = now - timedelta(minutes=threshold_minutes)
    nodes = (await session.execute(select(Node).where(
        Node.revoked_at.is_(None),
        Node.last_signal_received_at.is_not(None),  # never heard = not installed yet, not silent
        Node.last_signal_received_at < limit,
    ))).scalars().all()
    engine = AlertEngine(AlertRepository(session))
    for node in nodes:
        await engine.open_node_silent(node.node_id, now)
    # The same silence ends the node's connectivity session (the panel then shows it as disconnected).
    await close_silent_sessions(session, now=now, threshold_minutes=threshold_minutes)
    await session.flush()
    return len(nodes)


async def run_silence_monitor(session_maker: async_sessionmaker, *, every_seconds: int,
                              threshold_minutes: int) -> None:
    """Background loop started by the app lifespan."""
    while True:
        try:
            async with session_maker() as session:
                silent = await check_silent_nodes(session, now=datetime.now(timezone.utc),
                                                  threshold_minutes=threshold_minutes)
                await session.commit()
                if silent:
                    logger.warning(f"⚠️  {silent} nodo(s) sin enviar datos hace más de {threshold_minutes} min")
        except Exception as e:  # keep the loop alive; the next round retries
            logger.error(f"❌ Error revisando nodos en silencio: {e}")
        await asyncio.sleep(every_seconds)

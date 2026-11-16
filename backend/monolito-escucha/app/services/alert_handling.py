"""Marcar una alerta como atendida. Solo cambia `handled_by_user_id` y `handled_at`: nunca borra.

Mismo efecto que `POST /alerts/{id}/handle` de monolito-consulta, pero aquí el cambio pasa por la
sesión de escucha, así que el stream del panel lo ve y actualiza la tarjeta.
"""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert


async def mark_alert_handled(session: AsyncSession, alert_id: int, user_id: int) -> Alert | None:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        return None
    alert.handled_by_user_id = user_id
    alert.handled_at = datetime.now(timezone.utc)
    await session.commit()  # el evento sale al confirmar, antes de responder
    return alert

"""Alertas para el panel: stream SSE y marcado como atendida. Ambos exigen ID token de Firebase."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_user, require_user_or_query_token
from app.core.database import async_session_maker, get_db
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.firebase_auth import FirebaseUser
from app.models.alert import Alert
from app.models.app_user import AppUser
from app.services.alert_events import alert_payload
from app.services.alert_handling import mark_alert_handled
from app.services.alert_stream import alert_broadcaster, alert_event_stream

router = APIRouter(prefix="/alerts", tags=["alerts"])


async def _visible_alerts() -> list[dict]:
    """Alertas que el guardia debe ver ahora: mismo criterio que visible (terminada O sin atender)."""
    async with async_session_maker() as session:
        stmt = (
            select(Alert)
            .where(or_(Alert.ended_at.is_(None), Alert.handled_by_user_id.is_(None)))
            .order_by(Alert.started_at.desc())
        )
        return [alert_payload(alert) for alert in (await session.execute(stmt)).scalars().all()]


@router.get(
    "/stream",
    response_class=StreamingResponse,
    dependencies=[Depends(require_user_or_query_token)],
)
async def stream_alerts():
    """Server-Sent Events. Al conectarse envía las alertas visibles (`alert`), luego `alerts_ready`,
    y después cada cambio como `alert` con su estado completo.

    `visible: false` significa que la alerta ya terminó y fue atendida: el panel la quita, pero no se
    borra de la base de datos.
    """
    return StreamingResponse(
        alert_event_stream(alert_broadcaster, snapshot=_visible_alerts),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{alert_id}/handle")
async def handle_alert(
    alert_id: int,
    caller: FirebaseUser = Depends(require_user),
    session: AsyncSession = Depends(get_db),
):
    """Marca la alerta como atendida por el usuario que inició sesión. No la borra ni la cierra."""
    if not (caller.email and caller.email_verified):
        raise ForbiddenError("Your login has no verified email registered in app_user")
    user = (await session.execute(select(AppUser).where(AppUser.email == caller.email))).scalar_one_or_none()
    if user is None:
        raise ForbiddenError("Your login has no verified email registered in app_user")

    alert = await mark_alert_handled(session, alert_id, user.user_id)
    if alert is None:
        raise NotFoundError("Alert not found")
    return alert_payload(alert)

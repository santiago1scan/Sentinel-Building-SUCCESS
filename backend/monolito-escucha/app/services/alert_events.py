"""Convierte los cambios de la tabla `alert` en eventos del stream del panel.

Regla de visibilidad: igual que `GET /alerts/open` de monolito-consulta. Una alerta se ve en el panel
mientras no haya terminado O mientras nadie la haya atendido. Nunca se borra: al terminar o al
atenderse solo cambia su estado y el evento lo refleja con `visible`.

Se engancha a la sesión de SQLAlchemy, así que no hace falta tocar el motor de alertas ni cada
punto que confirma la transacción (MQTT, monitor de silencio, endpoints):
- before_flush / after_flush: se anotan las alertas nuevas y las que cambian ended_at o handled_by_user_id.
- after_commit: solo entonces se publica. Si la transacción falla, no sale nada.
- after_rollback: se descarta lo anotado.
"""
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.services.alert_stream import alert_broadcaster

_PENDING = "alert_stream_pending"
_READY = "alert_stream_ready"
_STATE_FIELDS = ("ended_at", "handled_by_user_id")


def is_visible_to_guard(alert: Alert) -> bool:
    """Misma regla que consulta: visible si no ha terminado o si nadie la ha atendido."""
    return alert.ended_at is None or alert.handled_by_user_id is None


def alert_payload(alert: Alert) -> dict:
    """Estado de la alerta para el panel, con la regla de visibilidad ya aplicada."""
    return {
        "alert_id": alert.alert_id,
        "event_uuid": alert.event_uuid,
        "alert_type": alert.alert_type,
        "alert_code": alert.alert_code,
        "direction": alert.direction,
        "node_id": alert.node_id,
        "sensor_id": alert.sensor_id,
        "metric_id": alert.metric_id,
        "started_at": alert.started_at.isoformat(),
        "last_seen_at": alert.last_seen_at.isoformat(),
        "ended_at": alert.ended_at.isoformat() if alert.ended_at else None,
        "handled_by_user_id": alert.handled_by_user_id,
        "handled_at": alert.handled_at.isoformat() if alert.handled_at else None,
        "visible": is_visible_to_guard(alert),
    }


def _state_changed(obj: Alert) -> bool:
    state = inspect(obj)
    return any(state.attrs[name].history.added for name in _STATE_FIELDS)


def _before_flush(session, flush_context, instances) -> None:
    pending = session.info.setdefault(_PENDING, [])
    for obj in session.new:
        if isinstance(obj, Alert):
            pending.append(obj)
    for obj in session.dirty:
        if isinstance(obj, Alert) and _state_changed(obj):
            pending.append(obj)


def _after_flush(session, flush_context) -> None:
    pending = session.info.pop(_PENDING, [])
    ready = session.info.setdefault(_READY, [])
    for obj in pending:
        ready.append(alert_payload(obj))


def _after_commit(session) -> None:
    for data in session.info.pop(_READY, []):
        alert_broadcaster.publish("alert", data)


def _after_rollback(session) -> None:
    session.info.pop(_PENDING, None)
    session.info.pop(_READY, None)


def register_alert_event_listeners() -> None:
    """Engancha los eventos a todas las sesiones. Es idempotente."""
    for name, fn in (
        ("before_flush", _before_flush),
        ("after_flush", _after_flush),
        ("after_commit", _after_commit),
        ("after_rollback", _after_rollback),
    ):
        if not event.contains(Session, name, fn):
            event.listen(Session, name, fn)

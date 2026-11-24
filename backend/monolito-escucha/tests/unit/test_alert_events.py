"""Los cambios de `alert` salen al stream solo al confirmarse, con la regla de visibilidad de consulta.

Regla: visible mientras no haya terminado O mientras nadie la haya atendido. Nunca se borra la fila.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.services.alert_events import register_alert_event_listeners
from app.services.alert_stream import alert_broadcaster

_next_id = iter(range(1, 1000))


@pytest.fixture
def session():
    register_alert_event_listeners()
    engine = create_engine("sqlite://")
    Alert.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _alert(code="OUT_OF_RANGE_ABOVE", node_id=2):
    # SQLite no genera IDs para BigInteger+Identity; se asigna a mano (la prueba mide el evento, no el ID).
    now = datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc)
    return Alert(
        alert_id=next(_next_id),
        event_uuid=f"uuid-{code}-{node_id}", alert_type="out_of_range", alert_code=code, direction="above",
        node_id=node_id, sensor_id=9, metric_id=4, started_at=now, last_seen_at=now, generated_at=now,
        reading_count=1,
    )


@pytest.fixture
def queue():
    q = alert_broadcaster.subscribe()
    yield q
    alert_broadcaster.unsubscribe(q)


def _drain(queue):
    items = []
    while not queue.empty():
        items.append(queue.get_nowait())
    return items


def test_alerta_nueva_se_publica_al_confirmar(session, queue):
    session.add(_alert())
    session.flush()
    assert _drain(queue) == []  # flush no es commit: aún no sale nada

    session.commit()

    events = _drain(queue)
    assert [name for name, _ in events] == ["alert"]
    assert events[0][1]["node_id"] == 2
    assert events[0][1]["visible"] is True


def test_terminada_sin_atender_sigue_visible(session, queue):
    alert = _alert()
    session.add(alert)
    session.commit()
    _drain(queue)

    alert.ended_at = datetime(2026, 11, 16, 10, 30, tzinfo=timezone.utc)
    session.commit()

    (name, data), = _drain(queue)
    assert name == "alert"
    assert data["ended_at"] is not None
    assert data["visible"] is True  # nadie la ha atendido: el guardia aún debe verla


def test_atendida_y_terminada_sale_del_panel_sin_borrarse(session, queue):
    alert = _alert()
    session.add(alert)
    session.commit()
    _drain(queue)

    alert.ended_at = datetime(2026, 11, 16, 10, 30, tzinfo=timezone.utc)
    alert.handled_by_user_id = 5
    alert.handled_at = datetime(2026, 11, 16, 10, 31, tzinfo=timezone.utc)
    session.commit()

    (name, data), = _drain(queue)
    assert data["visible"] is False
    assert data["handled_by_user_id"] == 5
    assert session.get(Alert, alert.alert_id) is not None  # la fila sigue existiendo


def test_atendida_pero_en_curso_sigue_visible(session, queue):
    alert = _alert()
    session.add(alert)
    session.commit()
    _drain(queue)

    alert.handled_by_user_id = 5
    session.commit()

    (_, data), = _drain(queue)
    assert data["visible"] is True


def test_rollback_no_publica_nada(session, queue):
    session.add(_alert())
    session.flush()
    session.rollback()

    assert _drain(queue) == []


def test_payload_has_severity(session, queue):
    alert = _alert(code="OUT_OF_RANGE_ABOVE", node_id=11)
    alert.severity = "leve"
    session.add(alert)
    session.commit()
    assert _drain(queue)[-1][1]["severity"] == "leve"


def test_severity_change_is_published(session, queue):
    # Upgrading to emergency changes neither ended_at nor handled_by_user_id: it must still reach the panel.
    alert = _alert(code="OUT_OF_RANGE_ABOVE", node_id=12)
    alert.severity = "leve"
    session.add(alert)
    session.commit()
    _drain(queue)

    alert.severity = "emergencia"
    session.commit()
    events = _drain(queue)
    assert len(events) == 1 and events[0][1]["severity"] == "emergencia"

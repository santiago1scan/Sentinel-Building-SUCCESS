import pytest

from app.datos.db import Database
from app.datos.repositorios.bitacora_repo import BitacoraRepo
from app.datos.repositorios.lecturas_repo import LecturasRepo
from app.datos.repositorios.outbox_repo import OutboxRepo


@pytest.fixture
def db(tmp_path):
    base = Database(tmp_path / "bridge_local.db")
    yield base
    base.close()


def lectura(event_id="evt-1"):
    return {
        "event_id": event_id,
        "node_id": "NODE-FLOOR-1",
        "sensor_id": "SENSOR-1-ACC",
        "sensor_type": "accelerometer",
        "generated_at": "2026-11-16T10:00:00.000+00:00",
    }


def agregado(uid="uid-1"):
    return {"message_uid": uid, "generated_at": "2026-11-16T10:00:01.000+00:00", "priority": "normal"}


def test_lecturas_no_duplica_el_mismo_event_id(db):
    repo = LecturasRepo(db)
    assert repo.save_readings([lectura("evt-1"), lectura("evt-2")]) == 2
    assert repo.save_readings([lectura("evt-1")]) == 0
    assert repo.count() == 2


def test_outbox_pendiente_y_marcado_como_enviado(db):
    repo = OutboxRepo(db)
    repo.save_aggregate(agregado("uid-1"))
    repo.save_aggregate(agregado("uid-2"))
    assert repo.counts() == {"pending": 2, "sent": 0}

    uid, _, attempts = repo.pending()[0]
    assert attempts == 0
    repo.mark_sent(uid, "sent_rest", "ok")
    assert repo.counts() == {"pending": 1, "sent": 1}


def test_outbox_registra_intentos_fallidos_sin_cambiar_estado(db):
    repo = OutboxRepo(db)
    repo.save_aggregate(agregado("uid-1"))
    repo.mark_attempt("uid-1", "timeout")
    repo.mark_attempt("uid-1", "timeout")
    (_, _, attempts), = repo.pending()
    assert attempts == 2
    assert repo.counts() == {"pending": 1, "sent": 0}


def test_outbox_no_duplica_el_mismo_message_uid(db):
    repo = OutboxRepo(db)
    repo.save_aggregate(agregado("uid-1"))
    repo.save_aggregate(agregado("uid-1"))
    assert repo.counts()["pending"] == 1


def test_bitacora_escribe_filas(db):
    BitacoraRepo(db).log("INFO", "arranque")
    (detalle,), = db.con.execute("SELECT detail FROM bridge_log").fetchall()
    assert detalle == "arranque"


def test_esquema_coincide_con_el_bridge_actual(db):
    tablas = {fila[0] for fila in db.con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"raw_reading", "aggregate_outbox", "bridge_log"} <= tablas

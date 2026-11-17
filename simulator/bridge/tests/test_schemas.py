import pytest

from app.presentacion.schemas import extraer_lecturas


def test_acepta_lista_directa():
    assert extraer_lecturas([{"event_id": "e1"}]) == [{"event_id": "e1"}]


def test_acepta_envoltura_readings():
    assert len(extraer_lecturas({"readings": [{"event_id": "e1"}, {"event_id": "e2"}]})) == 2


def test_rechaza_readings_que_no_es_lista():
    with pytest.raises(ValueError, match="debe ser una lista"):
        extraer_lecturas({"readings": "nope"})


def test_objeto_sin_readings_lanza_keyerror_como_el_original():
    with pytest.raises(KeyError):
        extraer_lecturas({"otra": []})

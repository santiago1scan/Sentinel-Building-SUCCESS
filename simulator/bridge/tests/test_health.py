def test_health_reporta_nodos_y_almacenamiento_vacio(cliente):
    respuesta = cliente.get("/health")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "ok"
    assert cuerpo["component"] == "bridge"
    assert cuerpo["nodes"] == []  # como el original: nodos = los que tienen token configurado
    assert cuerpo["mqtt_connected"] == {}
    assert cuerpo["storage"] == {"raw_readings": 0, "pending": 0, "sent": 0}

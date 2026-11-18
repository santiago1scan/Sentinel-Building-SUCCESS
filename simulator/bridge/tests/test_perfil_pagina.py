def test_perfil_trae_el_boton_de_desloguear_y_la_alerta_como_componentes(cliente):
    html = cliente.get("/perfil").text

    assert '<button id="desloguear" class="button-danger" type="button">Desloguear nodo</button>' in html
    assert '<p id="registroMensaje" class="alerta" role="alert" hidden></p>' in html
    assert "/api/registro/desloguear" in html
    assert 'id="deslogueoAcciones"' in html and "hidden" in html.split('id="deslogueoAcciones"')[1][:20]


def test_login_usa_la_misma_hoja_y_los_mismos_componentes_que_el_resto(cliente):
    html = cliente.get("/login").text

    assert '<link rel="stylesheet" href="/static/styles.css?v=' in html
    assert 'class="brand-mark"' in html
    assert '<button id="entrar" class="button-primary" type="button">Entrar con Google</button>' in html
    assert '<p id="estado" class="alerta" role="alert" hidden></p>' in html
    assert "/paginas/login/login.css?v=" in html


def test_login_pasa_al_perfil_cuando_la_sesion_es_valida(cliente):
    html = cliente.get("/login").text

    assert 'location.replace("/perfil")' in html

def test_los_estaticos_se_revalidan_siempre(cliente):
    for ruta in ("/static/styles.css", "/static/js/red.js", "/paginas/inicio/inicio.css"):
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 200
        assert respuesta.headers["cache-control"] == "no-cache", ruta
        assert "etag" in respuesta.headers, ruta


def test_las_hojas_y_scripts_llevan_version_en_la_url(cliente):
    import re

    versiones = set()
    for ruta, recurso in (("/", "/paginas/inicio/inicio.css"), ("/perfil", "/paginas/perfil/perfil.css"),
                          ("/login", "/paginas/login/login.css")):
        html = cliente.get(ruta).text
        for url in ("/static/styles.css", "/static/js/red.js", recurso):
            encontrado = re.search(re.escape(url) + r"\?v=([0-9a-f]{10})", html)
            assert encontrado, (ruta, url)
            versiones.add(encontrado.group(1))
    assert len(versiones) == 1  # una sola versión para todo el bridge
    assert cliente.get("/static/styles.css?v=" + versiones.pop()).status_code == 200

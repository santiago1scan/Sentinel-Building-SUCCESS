"""Plantillas Jinja2 de las páginas (autoescape activado para .html).

Estructura de paginas/:
    _base.html              documento común: <head>, hojas de estilo y bloques
    _componentes/macros.html  componentes reutilizables (encabezado, pie, sección, campo…)
    <pagina>/<pagina>.html  una página que extiende la base y usa los componentes
    <pagina>/<pagina>.css   los estilos de esa página
"""

from pathlib import Path

from fastapi.templating import Jinja2Templates

PAGINAS = Path(__file__).resolve().parent / "paginas"

plantillas = Jinja2Templates(directory=PAGINAS)

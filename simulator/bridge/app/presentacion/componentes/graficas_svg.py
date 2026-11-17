"""Componente de gráfica genérica: recibe los datos de una gráfica y devuelve un <svg>.

Sin dependencias ni JavaScript. Los colores salen de clases CSS (g-*) que define la
página con variables, así el mismo SVG sirve en tema claro y oscuro. Todo texto se
escapa antes de ponerlo en el SVG.
"""

import math
from datetime import datetime, timezone
from html import escape
from typing import Any

ANCHO, ALTO = 640, 240
IZQ, DER, ARR, ABJ = 56, 16, 36, 34
ANCHO_UTIL = ANCHO - IZQ - DER
ALTO_UTIL = ALTO - ARR - ABJ


def _abrir(titulo: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {ALTO}" '
            f'role="img" aria-label="{escape(titulo)}">')


def _titulo(titulo: str) -> str:
    return f'<text class="g-titulo" x="{IZQ}" y="20">{escape(titulo)}</text>'


def _hora(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%H:%M")


def _num(valor: float) -> str:
    return f"{valor:.3g}"


def _ejes_x(desde: float, hasta: float) -> str:
    return (f'<text class="g-texto" x="{IZQ}" y="{ALTO - 12}">{_hora(desde)}</text>'
            f'<text class="g-texto" x="{ANCHO - DER}" y="{ALTO - 12}" text-anchor="end">'
            f'{_hora(hasta)} UTC</text>')


def svg_vacio(datos: dict[str, Any]) -> str:
    mensaje = f"Sin lecturas en los últimos {datos['minutos']} min"
    return (_abrir(datos["titulo"]) + _titulo(datos["titulo"]) +
            f'<text class="g-texto" x="{ANCHO / 2}" y="{ALTO / 2}" text-anchor="middle">'
            f'{escape(mensaje)}</text></svg>')


def svg_linea(datos: dict[str, Any]) -> str:
    puntos = datos["puntos"]
    if not puntos:
        return svg_vacio(datos)

    desde, hasta = datos["desde_ts"], datos["hasta_ts"]
    valores = [v for _, v in puntos]
    vmin, vmax = min(valores), max(valores)
    if vmax == vmin:
        vmin, vmax = vmin - 1, vmax + 1
    margen = (vmax - vmin) * 0.05
    vmin, vmax = vmin - margen, vmax + margen

    def x(ts: float) -> float:
        return IZQ + (ts - desde) / (hasta - desde) * ANCHO_UTIL

    def y(valor: float) -> float:
        return ARR + ALTO_UTIL - (valor - vmin) / (vmax - vmin) * ALTO_UTIL

    partes = [_abrir(datos["titulo"]), _titulo(datos["titulo"])]
    for i in range(5):
        valor = vmin + i * (vmax - vmin) / 4
        py = y(valor)
        partes.append(f'<line class="g-eje" x1="{IZQ}" x2="{ANCHO - DER}" y1="{py:.1f}" y2="{py:.1f}"/>')
        partes.append(f'<text class="g-texto" x="{IZQ - 6}" y="{py + 4:.1f}" text-anchor="end">{_num(valor)}</text>')
    partes.append(_ejes_x(desde, hasta))

    trazo = " ".join(f"{x(ts):.1f},{y(v):.1f}" for ts, v in puntos)
    partes.append(f'<polyline class="g-linea" points="{trazo}"/>')
    ts_final, v_final = puntos[-1]
    partes.append(f'<circle class="g-punto" cx="{x(ts_final):.1f}" cy="{y(v_final):.1f}" r="3"/>')
    partes.append(f'<text class="g-texto" x="{ANCHO - DER}" y="20" text-anchor="end">'
                  f'último: {_num(v_final)} {escape(datos["unidad"])}</text>')
    partes.append("</svg>")
    return "".join(partes)


def svg_prioridad(datos: dict[str, Any]) -> str:
    cubos = datos["minutos_datos"]
    if not cubos:
        return svg_vacio(datos)

    desde, hasta = datos["desde_ts"], datos["hasta_ts"]
    ranuras = max(1, math.ceil((hasta - desde) / 60))
    ancho_barra = ANCHO_UTIL / ranuras
    maximo = max(c["normal"] + c["high"] + c["critical"] for c in cubos) or 1

    partes = [_abrir(datos["titulo"]), _titulo(datos["titulo"])]
    for i in range(5):
        valor = maximo * i / 4
        py = ARR + ALTO_UTIL - valor / maximo * ALTO_UTIL
        partes.append(f'<line class="g-eje" x1="{IZQ}" x2="{ANCHO - DER}" y1="{py:.1f}" y2="{py:.1f}"/>')
        partes.append(f'<text class="g-texto" x="{IZQ - 6}" y="{py + 4:.1f}" text-anchor="end">{_num(valor)}</text>')
    partes.append(_ejes_x(desde, hasta))

    for cubo in cubos:
        indice = int((cubo["ts"] - desde) // 60)
        if not 0 <= indice < ranuras:
            continue
        px = IZQ + indice * ancho_barra
        base = ARR + ALTO_UTIL
        for clase in ("normal", "high", "critical"):
            cantidad = cubo[clase]
            if not cantidad:
                continue
            alto = cantidad / maximo * ALTO_UTIL
            base -= alto
            partes.append(f'<rect class="g-{clase}" x="{px:.1f}" y="{base:.1f}" '
                          f'width="{max(ancho_barra - 1, 1):.1f}" height="{alto:.1f}"/>')

    leyenda_x = ANCHO - DER - 190
    for i, (clase, etiqueta) in enumerate((("normal", "normal"), ("high", "high"), ("critical", "critical"))):
        lx = leyenda_x + i * 66
        partes.append(f'<rect class="g-{clase}" x="{lx}" y="10" width="10" height="10"/>')
        partes.append(f'<text class="g-texto" x="{lx + 14}" y="19">{escape(etiqueta)}</text>')
    partes.append("</svg>")
    return "".join(partes)


def dibujar(datos: dict[str, Any]) -> str:
    """Punto de entrada del componente: elige el dibujo según el tipo de gráfica."""
    if datos["tipo"] == "linea":
        return svg_linea(datos)
    if datos["tipo"] == "prioridad":
        return svg_prioridad(datos)
    raise ValueError(f"Tipo de gráfica desconocido: {datos['tipo']}")

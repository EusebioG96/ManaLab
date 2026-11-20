#!/usr/bin/env python3
"""ML-280 (RED-02): cada botón de descarga envía a GoatCounter un evento propio por página e idioma. Sin red.

Esquema único: ``<tipo>-<página>-<idioma>[-<posición>]`` con tipo ``descarga``, ``descarga-movil`` (el «Descargar el ZIP igualmente»
del teléfono) o ``compartir-movil`` («Enviarme el enlace»). La posición solo va si la página tiene varios botones de descarga.
Los nombres los pone tools/construir_web.py (``{{EVENTO:tipo[:posicion]}}``) a partir de la ruta de la página: nadie los escribe a mano.

Recorre todo el HTML publicado y descarga.js; falla si un botón de descarga no tiene evento, si el nombre no cumple el patrón o no
corresponde a su página e idioma, si un nombre se repite, o si queda un nombre genérico («descarga», «guia-descarga»…).

Uso:  python3 tools/test_eventos_descarga.py
"""
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import construir_web  # noqa: E402

RAIZ = construir_web.RAIZ
NO_PUBLICADO = {".git", "plantillas", "docs", "tools"}  # lo publicado es el HTML generado, no sus fuentes
TIPOS = ("descarga", "descarga-movil", "compartir-movil")
PAGINAS = ("portada", "magic-online", "overlay", "logs", "coaches", "guia", "novedades", "learn", "player-log")
IDIOMAS = ("en", "es", "pt", "ja", "fr", "de", "it", "ko", "zh")
POSICIONES = ("cabecera", "hero", "motivos", "funciones", "descargar", "final", "arriba", "abajo")
PATRON = re.compile(
    r"(?P<tipo>%s)-(?P<pagina>%s)-(?P<idioma>%s)(?:-(?P<posicion>%s))?" % (
        "|".join(TIPOS), "|".join(PAGINAS), "|".join(IDIOMAS), "|".join(POSICIONES)))
GENERICOS = ("descarga", "guia-descarga", "novedades-descarga", "compartir-movil", "descarga-movil")
ATRIBUTOS_EVENTO = ("data-goatcounter-click", "data-goatcounter-title", "data-titulo")


class _Elementos(HTMLParser):
    """Etiquetas de apertura con sus atributos (también las de dentro de <template>)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.etiquetas = []

    def handle_starttag(self, etiqueta, atributos):
        self.etiquetas.append((etiqueta, {k: (v or "") for k, v in atributos}, self.getpos()[0]))


def _paginas():
    return sorted(p for p in RAIZ.rglob("*.html") if not NO_PUBLICADO & set(p.relative_to(RAIZ).parts))


def _etiquetas(ruta):
    analizador = _Elementos()
    analizador.feed(ruta.read_text(encoding="utf-8"))
    return analizador.etiquetas


def _es_de_descarga(a):
    """Un elemento es de descarga si baja el ZIP, lo marca para descarga.js, o ya declara un evento de descarga/compartir."""
    return ("data-descarga" in a or "data-a-bloque" in a or "data-compartir" in a or "download" in a
            or a.get("href", "").endswith("-portable.zip")
            or any(a.get(k, "").startswith(("descarga", "guia-descarga", "novedades-descarga", "compartir")) for k in ATRIBUTOS_EVENTO))


def _evento(a):
    return a.get("data-goatcounter-click") or a.get("data-titulo") or ""


class TestEventosDeDescarga(unittest.TestCase):
    def test_hay_paginas_y_botones(self):
        self.assertGreaterEqual(len(_paginas()), 25)
        total = sum(1 for p in _paginas() for _, a, _ in _etiquetas(p) if _es_de_descarga(a))
        self.assertGreaterEqual(total, 70)

    def test_cada_elemento_de_descarga_lleva_un_evento_con_el_patron(self):
        for ruta in _paginas():
            rel = ruta.relative_to(RAIZ)
            for etiqueta, a, linea in _etiquetas(ruta):
                if not _es_de_descarga(a):
                    continue
                with self.subTest(pagina=rel.as_posix(), linea=linea):
                    nombre = _evento(a)
                    self.assertTrue(nombre, f"{rel}:{linea}: <{etiqueta}> de descarga sin evento")
                    self.assertRegex(nombre, PATRON.pattern + r"$", f"{rel}:{linea}: «{nombre}» no cumple el patrón")

    def test_el_nombre_corresponde_a_su_pagina_e_idioma(self):
        for ruta in _paginas():
            rel = ruta.relative_to(RAIZ)
            pagina, idioma = construir_web.pagina_e_idioma(rel)
            for _, a, linea in _etiquetas(ruta):
                if not _es_de_descarga(a) or not _evento(a):
                    continue
                with self.subTest(pagina=rel.as_posix(), linea=linea):
                    m = PATRON.fullmatch(_evento(a))
                    if m:
                        self.assertEqual((m["pagina"], m["idioma"]), (pagina, idioma), f"{rel}:{linea}: {_evento(a)}")

    def test_click_y_titulo_coinciden(self):
        for ruta in _paginas():
            for _, a, linea in _etiquetas(ruta):
                if "data-goatcounter-click" in a and _es_de_descarga(a):
                    with self.subTest(pagina=ruta.relative_to(RAIZ).as_posix(), linea=linea):
                        self.assertEqual(a["data-goatcounter-click"], a.get("data-goatcounter-title"))

    def test_ningun_nombre_se_repite(self):
        vistos = {}
        for ruta in _paginas():
            rel = ruta.relative_to(RAIZ).as_posix()
            for _, a, linea in _etiquetas(ruta):
                nombre = _evento(a) if _es_de_descarga(a) else ""
                if not nombre:
                    continue
                with self.subTest(nombre=nombre):
                    self.assertNotIn(nombre, vistos, f"«{nombre}» en {rel}:{linea} y en {vistos.get(nombre)}")
                vistos.setdefault(nombre, f"{rel}:{linea}")

    def test_una_pagina_con_varios_botones_de_descarga_los_distingue_por_posicion(self):
        for ruta in _paginas():
            nombres = [_evento(a) for e, a, _ in _etiquetas(ruta) if _es_de_descarga(a) and a.get("data-goatcounter-click")]
            with self.subTest(pagina=ruta.relative_to(RAIZ).as_posix()):
                if len(nombres) > 1:
                    self.assertTrue(all(PATRON.fullmatch(n) and PATRON.fullmatch(n)["posicion"] for n in nombres), nombres)
                elif nombres and PATRON.fullmatch(nombres[0]):
                    self.assertIsNone(PATRON.fullmatch(nombres[0])["posicion"], nombres)

    def test_ningun_html_conserva_un_nombre_generico(self):
        for ruta in _paginas():
            for _, a, linea in _etiquetas(ruta):
                for atributo in ATRIBUTOS_EVENTO:
                    with self.subTest(pagina=ruta.relative_to(RAIZ).as_posix(), linea=linea, atributo=atributo):
                        self.assertNotIn(a.get(atributo), GENERICOS)

    def test_descarga_js_no_vuelve_al_nombre_generico(self):
        js = (RAIZ / "descarga.js").read_text(encoding="utf-8")
        for generico in GENERICOS:
            self.assertNotRegex(js, r"""["']%s["']""" % re.escape(generico), f"descarga.js usa «{generico}» a secas")
        # el evento del teléfono es el nombre que trae el elemento, no una constante
        self.assertIn('contar(boton.getAttribute("data-titulo"), boton.getAttribute("data-titulo"))', js)
        self.assertIn('contar(zip.getAttribute("data-titulo"), zip.getAttribute("data-titulo"))', js)
        # al volver a ordenador se devuelve el nombre guardado del botón
        self.assertIn("data-evento-original", js)

    def test_los_nombres_los_pone_el_generador(self):
        """Las fuentes no llevan nombres escritos a mano: solo marcadores {{EVENTO:...}}."""
        for ruta in sorted((RAIZ / "plantillas").rglob("*")):
            if not ruta.is_file():
                continue
            for n, linea in enumerate(ruta.read_text(encoding="utf-8").split("\n"), 1):
                for atributo in ATRIBUTOS_EVENTO:
                    for valor in re.findall(atributo + r'="([^"]*)"', linea):
                        if valor.startswith(("descarga", "guia-descarga", "novedades-descarga", "compartir")):
                            self.fail(f"{ruta.relative_to(RAIZ)}:{n}: nombre de evento escrito a mano ({valor}); usa {{{{EVENTO:...}}}}")


class TestGenerador(unittest.TestCase):
    def test_pagina_e_idioma_de_la_ruta(self):
        P = Path
        casos = {"index.html": ("portada", "en"), "es/index.html": ("portada", "es"), "pt/index.html": ("portada", "pt"),
                 "ja/index.html": ("portada", "ja"), "magic-online/index.html": ("magic-online", "en"),
                 "es/magic-online/index.html": ("magic-online", "es"), "detailed-logs/index.html": ("logs", "en"),
                 "es/registro-detallado/index.html": ("logs", "es"), "pt/coaches/index.html": ("coaches", "pt"),
                 "guia/guia_manalab_ja.html": ("guia", "ja"), "novedades/index.html": ("novedades", "en")}
        for ruta, esperado in casos.items():
            self.assertEqual(construir_web.pagina_e_idioma(P(ruta)), esperado, ruta)

    def test_tipo_desconocido_falla(self):
        with self.assertRaises(ValueError):
            construir_web.aplicar_eventos("{{EVENTO:otro}}", Path("index.html"))

    def test_marcador_con_y_sin_posicion(self):
        self.assertEqual(construir_web.aplicar_eventos("{{EVENTO:descarga:hero}} {{EVENTO:compartir-movil}}", Path("es/index.html")),
                         "descarga-portada-es-hero compartir-movil-portada-es")


if __name__ == "__main__":
    unittest.main()

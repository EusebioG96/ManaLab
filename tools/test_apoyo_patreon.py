#!/usr/bin/env python3
"""Comprueba la sección «Apoya el proyecto» de las portadas (en y es): dos botones primarios iguales, Ko-fi y Patreon, en la misma fila.

Uso:  python3 tools/test_apoyo_patreon.py
"""
import unittest
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PORTADAS = {"en": RAIZ / "index.html", "es": RAIZ / "es" / "index.html"}
KOFI = "https://ko-fi.com/eusebiog96"
PATREON = "https://www.patreon.com/ManaLab"


class Lector(HTMLParser):
    """Recoge los enlaces <a> (atributos y texto) y los párrafos de un trozo de HTML."""

    def __init__(self):
        super().__init__()
        self.enlaces = []        # [atributos, texto]
        self.parrafos = []
        self._a = None
        self._p = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._a = [{k: (v or "") for k, v in attrs}, ""]
        elif tag == "p":
            self._p = ""

    def handle_endtag(self, tag):
        if tag == "a" and self._a:
            self._a[1] = " ".join(self._a[1].split())
            self.enlaces.append(self._a)
            self._a = None
        elif tag == "p" and self._p is not None:
            self.parrafos.append(" ".join(self._p.split()))
            self._p = None

    def handle_data(self, d):
        if self._a:
            self._a[1] += d
        if self._p is not None:
            self._p += d


def seccion_apoyo(idioma):
    html = PORTADAS[idioma].read_text(encoding="utf-8")
    inicio = html.index('id="apoyo"')
    return html[inicio:html.index("</section>", inicio)]


def leer(idioma):
    lector = Lector()
    lector.feed(seccion_apoyo(idioma))
    return lector


def por_href(lector, href):
    return [e for e in lector.enlaces if e[0].get("href") == href]


class TestApoyoPatreon(unittest.TestCase):
    def test_boton_de_patreon(self):
        for idioma in PORTADAS:
            with self.subTest(idioma=idioma):
                encontrados = por_href(leer(idioma), PATREON)
                self.assertEqual(len(encontrados), 1, "debe haber exactamente un botón de Patreon en #apoyo")
                a, texto = encontrados[0]
                self.assertIn("noopener", a.get("rel", "").split())
                self.assertEqual(a.get("target"), "_blank")
                self.assertEqual(a["class"].split(), ["boton", "prim"])
                self.assertIn("Patreon", texto)

    def test_kofi_conserva_su_boton_primario(self):
        for idioma in PORTADAS:
            with self.subTest(idioma=idioma):
                encontrados = por_href(leer(idioma), KOFI)
                self.assertEqual(len(encontrados), 1)
                a, texto = encontrados[0]
                self.assertEqual(a.get("id"), "enlace-donar")
                self.assertEqual(a["class"].split(), ["boton", "prim"])
                self.assertEqual(a.get("target"), "_blank")
                self.assertIn("noopener", a.get("rel", "").split())
                self.assertIn("Ko-fi", texto)

    def test_ambos_botones_en_la_misma_fila(self):
        for idioma in PORTADAS:
            with self.subTest(idioma=idioma):
                html = " ".join(seccion_apoyo(idioma).split())
                i = html.index('id="enlace-donar"')
                fila = html[html.rindex('<div class="acciones"', 0, i):html.index("</div>", i)]
                self.assertIn(PATREON, fila)
                self.assertIn(KOFI, fila)

    def test_parrafo_nombra_las_dos_vias(self):
        for idioma in PORTADAS:
            with self.subTest(idioma=idioma):
                texto = " ".join(leer(idioma).parrafos)
                self.assertIn("Ko-fi", texto)
                self.assertIn("Patreon", texto)

    def test_patreon_solo_en_la_seccion_de_apoyo(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                self.assertEqual(ruta.read_text(encoding="utf-8").count(PATREON), 1)


if __name__ == "__main__":
    unittest.main()

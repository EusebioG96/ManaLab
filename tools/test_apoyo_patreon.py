#!/usr/bin/env python3
"""Comprueba que Ko-fi y Patreon aparecen juntos, con el mismo peso, donde la web explica cómo apoyar el proyecto o
conseguir la suscripción de IA:

- «Apoya el proyecto» de las portadas (en y es): dos botones primarios iguales en la misma fila.
- Sección de IA, tarjeta de funciones, FAQ (HTML y JSON-LD) de las portadas.
- Sección id="ia" de las 9 guías.
- Política de privacidad (es y en).

Uso:  python3 tools/test_apoyo_patreon.py
"""
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PORTADAS = {"en": RAIZ / "index.html", "es": RAIZ / "es" / "index.html"}
IDIOMAS_GUIA = ["es", "en", "de", "fr", "it", "pt", "ja", "ko", "zh"]
PRIVACIDAD = RAIZ / "privacy" / "index.html"
KOFI = "https://ko-fi.com/eusebiog96"
PATREON = "https://www.patreon.com/ManaLab"
FECHA_PRIVACIDAD = {"es": "30 de octubre de 2026", "en": "30 October 2026"}


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


def seccion(html, id_):
    """Texto HTML de la <section> con ese id (hasta su </section>)."""
    inicio = html.index(f'id="{id_}"')
    return html[inicio:html.index("</section>", inicio)]


def seccion_portada(idioma, id_):
    return seccion(PORTADAS[idioma].read_text(encoding="utf-8"), id_)


def leer(idioma, id_="apoyo"):
    lector = Lector()
    lector.feed(seccion_portada(idioma, id_))
    return lector


def por_href(lector, href):
    return [e for e in lector.enlaces if e[0].get("href") == href]


def texto_plano(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


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
                html = " ".join(seccion_portada(idioma, "apoyo").split())
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

    def test_cada_enlace_a_kofi_tiene_su_gemelo_de_patreon(self):
        """Donde hay un enlace a Ko-fi (apoyo, IA, tarjeta de funciones) hay uno a Patreon con el mismo estilo."""
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                lector = Lector()
                lector.feed(ruta.read_text(encoding="utf-8"))
                kofi, patreon = por_href(lector, KOFI), por_href(lector, PATREON)
                self.assertEqual(len(kofi), 3)
                self.assertEqual(len(patreon), len(kofi))
                for k, p in zip(kofi, patreon):
                    self.assertEqual(k[0].get("class"), p[0].get("class"), "mismo estilo")
                    self.assertEqual(k[0].get("style"), p[0].get("style"), "mismo estilo")
                    self.assertEqual(k[0].get("target"), p[0].get("target"))
                    self.assertIn("noopener", p[0].get("rel", "").split())

    def test_seccion_ia_con_las_dos_vias(self):
        for idioma in PORTADAS:
            with self.subTest(idioma=idioma):
                html = seccion_portada(idioma, "ia")
                texto = texto_plano(html)
                for palabra in ("Ko-fi", "Patreon", "Researcher", "Lab Partner"):
                    self.assertIn(palabra, texto)
                fila = html[html.rindex('<div class="acciones"', 0, html.index(PATREON)):]
                fila = fila[:fila.index("</div>")]
                self.assertIn(KOFI, fila)
                self.assertIn(PATREON, fila)
                self.assertEqual(len(por_href(leer(idioma, "ia"), PATREON)), 1)

    def test_faq_y_json_ld_nombran_las_dos_vias(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = ruta.read_text(encoding="utf-8")
                ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
                respuestas = [q["acceptedAnswer"]["text"] for nodo in ld["@graph"] if nodo["@type"] == "FAQPage"
                              for q in nodo["mainEntity"] if "Ko-fi" in q["acceptedAnswer"]["text"]]
                self.assertEqual(len(respuestas), 1)
                self.assertIn("Patreon", respuestas[0])
                self.assertIn("Lab Partner", respuestas[0])
                self.assertIn(" ".join(respuestas[0].split()), texto_plano(seccion_portada(idioma, "preguntas")))

    def test_guias_nombran_las_dos_vias_en_la_seccion_ia(self):
        for idioma in IDIOMAS_GUIA:
            with self.subTest(idioma=idioma):
                html = (RAIZ / "guia" / f"guia_manalab_{idioma}.html").read_text(encoding="utf-8")
                texto = texto_plano(seccion(html, "ia"))
                for palabra in ("Ko-fi", "patreon.com/ManaLab", "Researcher", "Lab Partner"):
                    self.assertIn(palabra, texto)

    def test_privacidad_describe_patreon(self):
        html = PRIVACIDAD.read_text(encoding="utf-8")
        for idioma, fecha in FECHA_PRIVACIDAD.items():
            with self.subTest(idioma=idioma):
                bloque = html[html.index(f'<section lang="{idioma}"'):]
                bloque = bloque[:bloque.index("</section>")]
                self.assertIn(fecha, bloque)
                self.assertGreaterEqual(bloque.count(PATREON), 1)
                self.assertGreaterEqual(bloque.count("Patreon"), 6)
                self.assertIn("Researcher", bloque)
                self.assertIn("Ko-fi", bloque)


if __name__ == "__main__":
    unittest.main()

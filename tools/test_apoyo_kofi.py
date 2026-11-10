#!/usr/bin/env python3
"""Ko-fi es la única vía de suscripción y donativos (ML-148, punto 10: la web ya no usa Patreon):

- «Apoya el proyecto» de las portadas (en y es): un único botón primario, el de Ko-fi.
- Sección de IA, tarjeta de funciones, FAQ (HTML y JSON-LD) de las portadas y de las páginas de Magic Online.
- Sección id="ia" de las 9 guías.
- Política de privacidad (es y en): fecha de actualización.
- «patreon» no aparece (sin distinguir mayúsculas) en ningún HTML, salvo una vez en cada guía: la frase de la barra
  lateral de la app 2.3.0, que todavía tiene el botón (se quita con ML-149).

Uso:  python3 tools/test_apoyo_kofi.py
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
KOFI_TIERS = "https://ko-fi.com/eusebiog96/tiers"   # suscribirse a la IA: directo a la membresía (no al perfil, que ofrece una donación)
FECHA_PRIVACIDAD = {"es": "10 de noviembre de 2026", "en": "10 November 2026"}   # día del cambio de ML-148
MAGIC_ONLINE = {"en": RAIZ / "magic-online" / "index.html", "es": RAIZ / "es" / "magic-online" / "index.html"}
BARRA_LATERAL = re.compile(r"♥\s*Patreon")   # frase que describe la barra lateral de la app publicada (2.3.0)


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
    # un tag en línea seguido de puntuación («<a>email</a>.») no debe dejar un espacio antes del signo
    return re.sub(r"\s+([.,;:!?])", r"\1", " ".join(re.sub(r"<[^>]+>", " ", html).split()))


def json_ld(ruta):
    html = ruta.read_text(encoding="utf-8")
    return json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))


def respuesta_ia_json(ruta):
    """Respuesta del FAQPage que habla de Ko-fi (la de «cómo consigo el análisis con IA»)."""
    respuestas = [q["acceptedAnswer"]["text"] for nodo in json_ld(ruta)["@graph"] if nodo["@type"] == "FAQPage"
                  for q in nodo["mainEntity"] if "Ko-fi" in q["acceptedAnswer"]["text"]]
    return respuestas


class TestApoyoKofi(unittest.TestCase):
    def test_boton_primario_de_apoyo(self):
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

    def test_apoyo_tiene_un_unico_boton(self):
        for idioma in PORTADAS:
            with self.subTest(idioma=idioma):
                html = " ".join(seccion_portada(idioma, "apoyo").split())
                i = html.index('id="enlace-donar"')
                fila = html[html.rindex('<div class="acciones"', 0, i):html.index("</div>", i)]
                self.assertEqual(fila.count("<a "), 1)
                self.assertNotIn('id="enlace-patreon"', html)

    def test_parrafo_de_apoyo_solo_nombra_ko_fi(self):
        for idioma in PORTADAS:
            with self.subTest(idioma=idioma):
                texto = " ".join(leer(idioma).parrafos)
                self.assertIn("Ko-fi", texto)
                self.assertNotIn("Patreon", texto)

    def test_enlaces_de_suscripcion_van_a_tiers(self):
        """Suscribirse (sección de IA y tarjeta de funciones) lleva a la membresía; donar, al perfil."""
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                lector = Lector()
                lector.feed(ruta.read_text(encoding="utf-8"))
                tiers = por_href(lector, KOFI_TIERS)
                self.assertEqual(len(tiers), 2)
                for a, _ in tiers:
                    self.assertEqual(a.get("target"), "_blank")
                    self.assertIn("noopener", a.get("rel", "").split())
                donar = por_href(lector, KOFI)
                self.assertEqual([a.get("id") for a, _ in donar], ["enlace-donar"])

    def test_seccion_ia_con_un_solo_boton(self):
        for idioma in PORTADAS:
            with self.subTest(idioma=idioma):
                html = seccion_portada(idioma, "ia")
                texto = texto_plano(html)
                self.assertIn("Ko-fi", texto)
                for palabra in ("Patreon", "Researcher", "Lab Partner"):
                    self.assertNotIn(palabra, texto)
                fila = html[html.rindex('<div class="acciones"', 0, html.index(KOFI_TIERS)):]
                fila = fila[:fila.index("</div>")]
                self.assertEqual(fila.count("<a "), 1)
                self.assertEqual(len(por_href(leer(idioma, "ia"), KOFI_TIERS)), 1)

    def test_faq_html_y_json_ld_iguales_y_solo_ko_fi(self):
        paginas = {**{f"portada-{i}": (r, "preguntas") for i, r in PORTADAS.items()},
                   **{f"magic-online-{i}": (r, "preguntas") for i, r in MAGIC_ONLINE.items()}}
        for nombre, (ruta, id_) in paginas.items():
            with self.subTest(pagina=nombre):
                respuestas = respuesta_ia_json(ruta)
                self.assertEqual(len(respuestas), 1)
                self.assertNotIn("Patreon", respuestas[0])
                self.assertNotIn("Lab Partner", respuestas[0])
                html = ruta.read_text(encoding="utf-8")
                html = re.sub(r'<script type="application/ld\+json">.*?</script>', "", html, flags=re.S)   # solo el HTML visible
                self.assertIn(" ".join(respuestas[0].split()), texto_plano(html.replace("&#x27;", "'")))

    def test_guias_ia_solo_ko_fi(self):
        for idioma in IDIOMAS_GUIA:
            with self.subTest(idioma=idioma):
                html = (RAIZ / "guia" / f"guia_manalab_{idioma}.html").read_text(encoding="utf-8")
                texto = texto_plano(seccion(html, "ia"))
                self.assertIn("Ko-fi", texto)
                for palabra in ("Patreon", "patreon.com", "Researcher", "Lab Partner"):
                    self.assertNotIn(palabra, texto)

    def test_privacidad_actualizada_y_con_ko_fi(self):
        html = PRIVACIDAD.read_text(encoding="utf-8")
        for idioma, fecha in FECHA_PRIVACIDAD.items():
            with self.subTest(idioma=idioma):
                bloque = html[html.index(f'<section lang="{idioma}"'):]
                bloque = bloque[:bloque.index("</section>")]
                self.assertIn(fecha, bloque)
                self.assertIn("Ko-fi", bloque)


class TestSinPatreon(unittest.TestCase):
    def test_ninguna_pagina_nombra_patreon_salvo_la_barra_lateral_de_las_guias(self):
        paginas = sorted(p for p in RAIZ.rglob("*.html") if ".git" not in p.parts)
        self.assertGreater(len(paginas), 20)
        for ruta in paginas:
            with self.subTest(pagina=str(ruta.relative_to(RAIZ))):
                texto = ruta.read_text(encoding="utf-8")
                total = len(re.findall("patreon", texto, re.I))
                if ruta.parent == RAIZ / "guia":
                    # una sola mención, en la frase de la barra lateral de la app 2.3.0
                    self.assertEqual(total, 1)
                    self.assertEqual(len(BARRA_LATERAL.findall(texto)), 1)
                else:
                    self.assertEqual(total, 0)

    def test_barra_lateral_en_las_9_guias(self):
        for idioma in IDIOMAS_GUIA:
            with self.subTest(idioma=idioma):
                texto = (RAIZ / "guia" / f"guia_manalab_{idioma}.html").read_text(encoding="utf-8")
                self.assertEqual(len(BARRA_LATERAL.findall(texto)), 1)
                self.assertIn("♥ Ko-fi", texto)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""ML-274 (WEB-05): ni Ko-fi ni Patreon en la web, y los enlaces de Metafy salen solo de contenido.json.

- Ningún .html, plantilla ni README nombra Ko-fi o Patreon.
- La frase corta «Tus datos se quedan en tu PC…» (con o sin «salvo que pidas la IA») ya no está en ninguna página.
- ``enlace_suscripcion_ia`` vacío: en lugar del botón «Suscribirme en Metafy» sale el texto «muy pronto», sin enlace.
  Con valor: los botones de la IA llevan ese enlace. Nunca un botón muerto.
- ``enlace_apoyo_metafy`` vacío: no hay bloque «Apoya el proyecto». Con valor: un botón grande ``.b-metafy`` con el logotipo.
- Las respuestas de «¿cómo consigo la IA?» (HTML y ld+json) dicen lo mismo y nombran Metafy.

Uso:  python3 -m pytest tools/test_enlaces_metafy.py
"""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import construir_web  # noqa: E402

RAIZ = construir_web.RAIZ
PORTADAS = {"en": "index.html", "es": "es/index.html", "pt": "pt/index.html", "ja": "ja/index.html"}
PORTADAS_CON_APOYO = ("en", "es")  # el bloque «Apoya el proyecto» solo estaba en inglés y español
PAGINAS_CON_FAQ = {**{f"portada-{i}": r for i, r in PORTADAS.items()},
                   "magic-online-en": "magic-online/index.html", "magic-online-es": "es/magic-online/index.html"}
IDIOMAS_GUIA = ["es", "en", "de", "fr", "it", "pt", "ja", "ko", "zh"]
ENLACE_IA = "https://metafy.gg/@manalab/ia"
ENLACE_APOYO = "https://www.metafy.gg/@manalab"
# texto «muy pronto» de cada portada (los botones de la IA sin enlace)
PRONTO = {"en": "Subscription on Metafy: coming soon", "es": "Suscripción en Metafy: muy pronto",
          "pt": "Assinatura no Metafy: em breve", "ja": "Metafyでの購読：まもなく開始"}
# la frase que ya no puede salir en ninguna página
FRASES_FUERA = ["Tus datos se quedan en tu PC", "Your data stays on your PC", "Seus dados ficam no seu PC", "AIを使わない限り、データはPC内に保存"]


def _construir(contenido: dict) -> Path:
    """Construye toda la web en una carpeta temporal con ese contenido.json y devuelve la carpeta."""
    base = Path(tempfile.mkdtemp())
    raiz = base / "repo"
    raiz.mkdir()
    shutil.copytree(RAIZ / construir_web.CARPETA_PLANTILLAS, raiz / construir_web.CARPETA_PLANTILLAS)
    shutil.copy(RAIZ / construir_web.ARCHIVO_VERSION, raiz / construir_web.ARCHIVO_VERSION)
    (raiz / construir_web.ARCHIVO_CONTENIDO).write_text(json.dumps(contenido), encoding="utf-8")
    salida = base / "salida"
    construir_web.construir(raiz, salida)
    return salida


def _contenido(**campos) -> dict:
    return {"v": 1, "enlace_apoyo_metafy": "", "enlace_suscripcion_ia": "", "interruptores": {"banner_mdn": True}, **campos}


def _anclas(html: str) -> list[str]:
    return re.findall(r"<a [^>]*>", html)


def botones_muertos(html: str) -> list[str]:
    """Enlaces de Metafy (botón de suscripción o de apoyo) sin destino real."""
    marcados = [a for a in _anclas(html) if "metafy-" in a or "b-metafy" in a]
    return [a for a in marcados if not re.search(r'href="https://(www\.)?metafy\.gg/[^"]+"', a)]


def _texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


class TestSinKofiNiPatreon(unittest.TestCase):
    def test_ninguna_pagina_ni_plantilla_nombra_ko_fi_o_patreon(self):
        archivos = [p for p in RAIZ.rglob("*") if p.is_file() and p.suffix in (".html", ".tpl", ".txt", ".pagina", ".md") and ".git" not in p.parts]
        self.assertGreater(len(archivos), 150)
        for ruta in archivos:
            if ruta.relative_to(RAIZ).parts[0] in ("docs", "tools"):
                continue
            with self.subTest(archivo=str(ruta.relative_to(RAIZ))):
                self.assertIsNone(re.search(r"ko-?fi|patreon", _texto(ruta), re.I))

    def test_la_frase_corta_de_datos_ya_no_esta_y_la_franja_si(self):
        for ruta in RAIZ.rglob("*.html"):
            if ".git" in ruta.parts:
                continue
            html = _texto(ruta)
            for frase in FRASES_FUERA:
                with self.subTest(pagina=str(ruta.relative_to(RAIZ)), frase=frase):
                    self.assertNotIn(frase, html)
        self.assertIn("Partidas, capturas y estadísticas se quedan en una carpeta de tu ordenador.", _texto(RAIZ / "es/index.html"))

    def test_nada_dice_que_metafy_lo_sostiene(self):
        for ruta in RAIZ.rglob("*.html"):
            if ".git" not in ruta.parts:
                self.assertNotRegex(_texto(ruta), r"(?i)lo sostiene Metafy|sustained by Metafy|backed by Metafy")


class TestSuscripcionIa(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sin = _construir(_contenido())
        cls.con = _construir(_contenido(enlace_suscripcion_ia=ENLACE_IA))

    def test_contenido_real_no_tiene_enlace_todavia(self):
        datos = json.loads(_texto(RAIZ / "contenido.json"))
        self.assertEqual(datos["enlace_suscripcion_ia"], "")
        self.assertEqual(datos["enlace_apoyo_metafy"], "")

    def test_sin_enlace_sale_el_texto_muy_pronto_y_ningun_enlace_a_metafy(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = _texto(self.sin / ruta)
                self.assertEqual(html.count(f'<span class="pronto">{PRONTO[idioma]}</span>'), 2)  # tarjeta de funciones y sección de IA
                self.assertNotIn("metafy.gg/@", html)
                self.assertEqual(botones_muertos(html), [])
                self.assertFalse([a for a in _anclas(html) if "metafy-ia" in a or "metafy-funciones" in a])

    def test_con_enlace_los_dos_botones_llevan_ese_enlace(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = _texto(self.con / ruta)
                botones = [a for a in _anclas(html) if f'href="{ENLACE_IA}"' in a]
                self.assertEqual(len(botones), 2)
                titulos = sorted(re.search(r'data-goatcounter-title="([^"]+)"', a).group(1) for a in botones)
                self.assertEqual(titulos, [f"metafy-funciones-{idioma}", f"metafy-ia-{idioma}"])
                for a in botones:
                    self.assertIn('target="_blank"', a)
                    self.assertIn('rel="noopener"', a)
                    self.assertIn('data-goatcounter-click="apoyo"', a)
                self.assertNotIn('class="pronto"', html)
                self.assertEqual(botones_muertos(html), [])

    def test_el_boton_principal_de_la_ia_es_primario(self):
        html = _texto(self.con / "es/index.html")
        self.assertRegex(html, r'<a class="boton prim" href="' + re.escape(ENLACE_IA) + '"')

    def test_enlace_no_valido_rompe_la_construccion(self):
        for malo in ("http://metafy.gg/x", "https://evil.com/metafy.gg", "https://user@metafy.gg/x", "https://metafy.gg:8443/x", "javascript:alert(1)"):
            with self.subTest(enlace=malo):
                with self.assertRaises(ValueError):
                    _construir(_contenido(enlace_suscripcion_ia=malo))

    def test_mutacion_un_boton_sin_destino_se_detecta(self):
        original = construir_web._bloque_suscripcion_ia
        construir_web._bloque_suscripcion_ia = lambda parametros, enlace: (
            f'<a class="boton prim" href="" data-goatcounter-title="{parametros["medicion"]}"><span>{parametros["texto"]}</span></a>')
        try:
            mutada = _construir(_contenido())
        finally:
            construir_web._bloque_suscripcion_ia = original
        self.assertTrue(botones_muertos(_texto(mutada / "es/index.html")))
        self.assertEqual(botones_muertos(_texto(self.sin / "es/index.html")), [])


class TestApoyoMetafy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sin = _construir(_contenido())
        cls.con = _construir(_contenido(enlace_apoyo_metafy=ENLACE_APOYO))

    def test_sin_enlace_no_hay_bloque_de_apoyo(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = _texto(self.sin / ruta)
                self.assertNotIn('id="apoyo"', html)
                self.assertNotIn("b-metafy", html.replace(".b-metafy", ""))
                self.assertNotIn("metafy.svg", html)

    def test_con_enlace_en_y_es_llevan_el_boton_grande_con_logotipo(self):
        for idioma in PORTADAS_CON_APOYO:
            with self.subTest(idioma=idioma):
                html = _texto(self.con / PORTADAS[idioma])
                bloque = html[html.index('id="apoyo"'):]
                bloque = bloque[:bloque.index("</section>")]
                botones = re.findall(r'<a class="b-metafy"[^>]*>.*?</a>', bloque, re.S)
                self.assertEqual(len(botones), 1)
                self.assertIn(f'href="{ENLACE_APOYO}"', botones[0])
                self.assertIn('<img src="/img/metafy.svg" alt=""', botones[0])
                self.assertEqual(botones_muertos(html), [])

    def test_con_enlace_pt_y_ja_siguen_sin_bloque(self):
        for idioma in ("pt", "ja"):
            self.assertNotIn('id="apoyo"', _texto(self.con / PORTADAS[idioma]))

    def test_logotipo_copiado_a_la_web(self):
        svg = RAIZ / "img" / "metafy.svg"
        self.assertTrue(svg.is_file())
        self.assertTrue(_texto(svg).lstrip().startswith("<svg"))

    def test_el_css_del_boton_esta_en_la_hoja_de_sitio(self):
        self.assertIn(".b-metafy {", _texto(RAIZ / "plantillas" / "css_sitio.tpl"))


def _respuestas_ia(html: str) -> list[str]:
    """Respuestas del FAQPage (ld+json) que hablan de cómo conseguir el análisis con IA (la que abre con Metafy y el precio)."""
    datos = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
    return [q["acceptedAnswer"]["text"] for nodo in datos["@graph"] if nodo["@type"] == "FAQPage"
            for q in nodo["mainEntity"] if "Metafy" in q["acceptedAnswer"]["text"] and "5" in q["acceptedAnswer"]["text"] and "Metafy" in q["acceptedAnswer"]["text"][:60]]


def _texto_plano(html: str) -> str:
    return re.sub(r"\s+([.,;:!?])", r"\1", " ".join(re.sub(r"<[^>]+>", " ", html).split()))


class TestTextosDeLaIa(unittest.TestCase):
    def test_faq_html_y_json_ld_dicen_lo_mismo_y_nombran_metafy(self):
        for nombre, ruta in PAGINAS_CON_FAQ.items():
            with self.subTest(pagina=nombre):
                html = _texto(RAIZ / ruta)
                respuestas = _respuestas_ia(html)
                self.assertEqual(len(respuestas), 1)
                visible = re.sub(r'<script type="application/ld\+json">.*?</script>', "", html, flags=re.S).replace("&#x27;", "'")
                self.assertIn(re.sub(r"\s+", "", respuestas[0]), re.sub(r"\s+", "", _texto_plano(visible)))  # sin espacios: el japonés no los lleva ante un enlace

    def test_guias_explican_la_suscripcion_con_metafy_y_sin_botones_de_patreon(self):
        for idioma in IDIOMAS_GUIA:
            with self.subTest(idioma=idioma):
                html = _texto(RAIZ / "guia" / f"guia_manalab_{idioma}.html")
                seccion = html[html.index('id="ia"'):]
                seccion = _texto_plano(seccion[:seccion.index("</section>")])
                self.assertIn("Metafy", seccion)
                self.assertNotIn("♥", html)

    def test_privacidad_cuenta_la_suscripcion_con_metafy(self):
        html = _texto(RAIZ / "privacy" / "index.html")
        for idioma, fecha in {"es": "14 de noviembre de 2026", "en": "14 November 2026"}.items():
            with self.subTest(idioma=idioma):
                bloque = html[html.index(f'<section lang="{idioma}"'):]
                bloque = bloque[:bloque.index("</section>")]
                self.assertIn(fecha, bloque)
                self.assertIn("Metafy", bloque)
                self.assertRegex(bloque, r"(?s)Metafy[^<]*(recibe|receives)")

    def test_seguridad_habla_del_apoyo_en_metafy(self):
        self.assertIn("el apoyo en Metafy va para eso", _texto(RAIZ / "es" / "seguridad" / "index.html"))
        self.assertIn("the support on Metafy goes toward it", _texto(RAIZ / "safety" / "index.html"))


if __name__ == "__main__":
    unittest.main()

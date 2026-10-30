#!/usr/bin/env python3
"""Comprueba la página «¿Es seguro ManaLab?» (en: /safety/, es: /es/seguridad/): estructura gemela en los dos idiomas,
hreflang recíproco, entradas en el sitemap, sin huecos [TÚ] y sin números de versión fijos (se quedarían viejos).

Uso:  python3 tools/test_pagina_seguridad.py
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PAGINAS = {"en": RAIZ / "safety" / "index.html", "es": RAIZ / "es" / "seguridad" / "index.html"}
URLS = {"en": "https://manalab.es/safety/", "es": "https://manalab.es/es/seguridad/"}
IDS = ["lee", "conexiones", "comprobar", "firma", "codigo", "dudas"]


def leer(lang):
    return PAGINAS[lang].read_text(encoding="utf-8")


class TestPaginaSeguridad(unittest.TestCase):
    def test_existen_y_tienen_su_idioma(self):
        for lang in PAGINAS:
            with self.subTest(lang=lang):
                self.assertIn(f'<html lang="{lang}">', leer(lang))

    def test_secciones_gemelas(self):
        for lang in PAGINAS:
            ids = re.findall(r'<section class="tarjeta" id="([a-z]+)"', leer(lang))
            self.assertEqual(ids, IDS, lang)

    def test_canonical_y_hreflang(self):
        for lang in PAGINAS:
            t = leer(lang)
            with self.subTest(lang=lang):
                self.assertIn(f'<link href="{URLS[lang]}" rel="canonical"/>', t)
                for h, u in (("en", URLS["en"]), ("es", URLS["es"]), ("x-default", URLS["en"])):
                    self.assertIn(f'<link href="{u}" hreflang="{h}" rel="alternate"/>', t)

    def test_sitemap(self):
        s = (RAIZ / "sitemap.xml").read_text(encoding="utf-8")
        for u in URLS.values():
            self.assertEqual(s.count(f"<loc>{u}</loc>"), 1, u)

    def test_sin_huecos_ni_versiones_fijas(self):
        for lang in PAGINAS:
            t = leer(lang)
            with self.subTest(lang=lang):
                self.assertNotIn("[TÚ", t)
                self.assertNotIn("TÚ:", t)
                self.assertIsNone(re.search(r"\b\d+\.\d+\.\d+\b", re.sub(r"<style.*?</style>", "", t, flags=re.S)))

    def test_enlaces_decididos(self):
        for lang in PAGINAS:
            t = leer(lang)
            with self.subTest(lang=lang):
                self.assertEqual(t.count('href="https://github.com/EusebioG96/ManaLab/releases/latest"'), 2)
                self.assertIn('href="mailto:manalab.app@gmail.com"', t)

    def test_comando_hash_con_comodin(self):
        for lang in PAGINAS:
            t = leer(lang)
            with self.subTest(lang=lang):
                self.assertIn(r"Get-FileHash .\ManaLab*.zip -Algorithm SHA256", t)
                self.assertNotIn(r".\ManaLab.zip", t)

    def test_enlaza_privacidad_y_firma_manalab(self):
        for lang in PAGINAS:
            t = leer(lang)
            with self.subTest(lang=lang):
                self.assertIn('href="/privacy/#%s"' % lang, t)
                self.assertIn("— ManaLab</p>", t)
                self.assertNotIn("DeepSeek", t)
                self.assertNotIn("monitor", t.split("<main")[1] if "<main" in t else t)

    def test_enlaces_desde_portada_y_pie(self):
        destino = {"en": "/safety/", "es": "/es/seguridad/"}
        portadas = {"en": RAIZ / "index.html", "es": RAIZ / "es" / "index.html"}
        for lang, ruta in portadas.items():
            t = ruta.read_text(encoding="utf-8")
            d = destino[lang]
            with self.subTest(lang=lang):
                # enlace bajo el botón de descarga, entre las notas de SmartScreen
                self.assertRegex(t, r'<p class="nota-smartscreen"><a href="%s">[^<]+→</a></p>' % re.escape(d))
                # pie con el enlace, junto a Privacidad
                pie = t[t.index("<footer>"):]
                self.assertIn('<a href="%s">' % d, pie)
                # FAQ: «Más detalles» en las respuestas de datos y de aviso de Windows
                self.assertEqual(t.count('<a href="%s">' % d), 4)
                self.assertEqual(len(re.findall(r"<p>(?:More details|Más detalles): <a href=\"%s\">" % re.escape(d), t)), 2)
        for lang in PAGINAS:
            pie = leer(lang)
            pie = pie[pie.index("<footer>"):]
            with self.subTest(pie=lang):
                self.assertIn('<a href="%s">' % destino[lang], pie)


if __name__ == "__main__":
    unittest.main()

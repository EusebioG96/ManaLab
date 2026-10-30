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


if __name__ == "__main__":
    unittest.main()
